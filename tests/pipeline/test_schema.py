import sqlite3

from pipeline.schema import TABLES


def test_every_table_has_primary_key_columns():
    for table in TABLES.values():
        assert set(table.pk) <= set(table.column_names), table.name


def test_arrow_schema_matches_columns():
    for table in TABLES.values():
        assert table.arrow_schema.names == table.column_names


def test_sqlite_and_postgres_ddl_generate():
    conn = sqlite3.connect(":memory:")
    for table in TABLES.values():
        conn.execute(table.sqlite_ddl())
        assert "PRIMARY KEY" in table.postgres_ddl()


def test_scraper_database_matches_declared_columns(sample_db):
    """The synthetic DB is built from schema.py, so a drift here means schema.py is inconsistent."""
    conn = sqlite3.connect(sample_db)
    for table in TABLES.values():
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table.name})")]
        assert cols == table.column_names
