import sqlite3

import pyarrow.parquet as pq

from pipeline import extract
from pipeline.sample_data import create_sample_db
from pipeline.schema import TABLES


def test_row_counts_match_sqlite(sample_db, tmp_path):
    lake = tmp_path / "lake"
    counts = extract.run(sample_db, lake)
    conn = sqlite3.connect(sample_db)
    for name, n in counts.items():
        assert n == conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        assert extract.read_table(TABLES[name], lake).count_rows() == n


def test_matches_are_partitioned_by_patch(sample_db, tmp_path):
    lake = tmp_path / "lake"
    extract.run(sample_db, lake)
    assert (lake / "matches" / "patch_version=16.3").is_dir()
    assert (lake / "participants" / "part-0.parquet").is_file()


def test_patch_like_16_10_is_not_parsed_as_float(tmp_path):
    db = create_sample_db(tmp_path / "s.sqlite", matches=5, patch="16.10")
    lake = tmp_path / "lake"
    extract.run(db, lake)
    table = extract.read_table(TABLES["matches"], lake).to_table()
    assert set(table.column("patch_version").to_pylist()) == {"16.10"}


def test_extract_is_idempotent(sample_db, tmp_path):
    lake = tmp_path / "lake"
    first = extract.run(sample_db, lake)
    second = extract.run(sample_db, lake)
    assert first == second
    assert extract.read_table(TABLES["matches"], lake).count_rows() == first["matches"]


def test_parquet_uses_declared_types(sample_db, tmp_path):
    lake = tmp_path / "lake"
    extract.run(sample_db, lake)
    schema = pq.read_schema(lake / "participants" / "part-0.parquet")
    assert schema == TABLES["participants"].arrow_schema
