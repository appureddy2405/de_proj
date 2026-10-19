# Data-engineering upgrade - what changed

## Added
| Path | Purpose |
|---|---|
| `pipeline/` | schema (single source of truth), extract (SQLite→Parquet), load (Parquet→Postgres), quality checks, CLI, synthetic sample data |
| `dbt_lol/` | dbt project: 5 staging views, 4 marts, 24 tests (generic + singular) |
| `orchestration/dags/lol_pipeline.py` | Airflow DAG (daily, retries, quality gates) |
| `dashboard/app.py` | Streamlit dashboard over the marts |
| `docker/`, `docker-compose.yml`, `.dockerignore` | Postgres, one-off pipeline run, Airflow, dashboard |
| `.github/workflows/ci.yml` | lint, tests (with Postgres service), end-to-end pipeline run, Docker builds |
| `tests/pipeline/` | 22 new tests (schema, extract, quality, Postgres load) |
| `Makefile`, `ruff.toml`, `pytest.ini`, `.env.example`, `requirements-pipeline.txt`, `requirements-dev.txt` | tooling |

## Changed in existing files
- `__init__.py` at the repo root was **removed**. It only re-exported names with package-relative imports, nothing imported it
  (all scripts use absolute imports), and it made pytest fail on every test at setup. With it gone the 57 original tests pass.
- `requirements.txt`: `python-dotenv==1.0.1` → `>=1.0.1` (dbt-core requires >=1.2; the exact pin made the two uninstallable together).
- `.gitignore`: ignores pipeline outputs, `data/db/*.sqlite*`, `data/logs/`.
- `README.md`: new "Analytics Pipeline" section, structure/features updated, test counts corrected, broken `TEST_STRUCTURE.md` link fixed.

## Verified vs. not verified
Verified (run end to end): extract, Postgres load (idempotent, replace mode), quality gates incl. failure path,
dbt build (33/33 on PostgreSQL 16, dbt-core 1.12.6), 79 tests, Streamlit app (headless AppTest), DAG parsing under Airflow 2.10.5.
Not run here (no Docker available): the Docker images / compose stack, running tasks inside Airflow, the GitHub Actions workflow itself.
