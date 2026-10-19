"""Integration tests: need a reachable Postgres (set WAREHOUSE_DSN). Skipped otherwise."""
import os
import uuid

import psycopg
import pytest

from pipeline import extract, load, quality

pytestmark = pytest.mark.integration

DSN = os.getenv("WAREHOUSE_DSN")
if not DSN:
    pytest.skip("WAREHOUSE_DSN not set", allow_module_level=True)


@pytest.fixture
def schema():
    name = f"raw_test_{uuid.uuid4().hex[:8]}"
    yield name
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {name} CASCADE")


@pytest.fixture
def lake(sample_db, tmp_path):
    extract.run(sample_db, tmp_path / "lake")
    return tmp_path / "lake"


def _count(schema, table):
    with psycopg.connect(DSN) as conn:
        return conn.execute(f"SELECT count(*) FROM {schema}.{table}").fetchone()[0]


def test_load_matches_lake_row_counts(lake, schema):
    counts = load.run(lake, DSN, schema)
    assert counts["matches"] == 40
    assert counts["participants"] == 400
    assert _count(schema, "participant_items") == 2800


def test_reload_is_idempotent(lake, schema):
    first = load.run(lake, DSN, schema)
    second = load.run(lake, DSN, schema)
    assert first == second


def test_upsert_updates_changed_rows(lake, schema):
    load.run(lake, DSN, schema)
    with psycopg.connect(DSN) as conn:
        conn.execute(f"UPDATE {schema}.matches SET queue_type = 'stale'")
    load.run(lake, DSN, schema)
    with psycopg.connect(DSN) as conn:
        stale = conn.execute(f"SELECT count(*) FROM {schema}.matches WHERE queue_type = 'stale'").fetchone()[0]
    assert stale == 0


def test_replace_mode_removes_rows_not_in_lake(lake, schema):
    load.run(lake, DSN, schema)
    with psycopg.connect(DSN) as conn:
        conn.execute(f"INSERT INTO {schema}.champions VALUES (9999, 'Ghost', '')")
    assert _count(schema, "champions") == 31
    load.run(lake, DSN, schema, mode="replace")
    assert _count(schema, "champions") == 30


def test_audit_table_records_each_run(lake, schema):
    load.run(lake, DSN, schema)
    load.run(lake, DSN, schema)
    with psycopg.connect(DSN) as conn:
        runs = conn.execute(f"SELECT count(DISTINCT run_id) FROM {schema}._load_audit").fetchone()[0]
    assert runs == 2


def test_quality_suite_runs_on_postgres(lake, schema):
    load.run(lake, DSN, schema)
    with psycopg.connect(DSN) as conn:
        report = quality.run_checks(conn, prefix=f"{schema}.", target="warehouse")
    assert report["passed"]
