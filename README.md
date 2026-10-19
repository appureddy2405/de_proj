# League of Legends Ranked Data Pipeline

By **Appu**. An end-to-end data pipeline for League of Legends ranked matches: an async scraper for the Riot API, a Parquet data lake, a Postgres warehouse, dbt transformations with tests, data quality gates, Airflow orchestration, Docker, CI and a Streamlit dashboard.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Postgres](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.12-FF694B?logo=dbt&logoColor=white)
![Airflow](https://img.shields.io/badge/Airflow-2.10-017CEE?logo=apacheairflow&logoColor=white)
![Parquet](https://img.shields.io/badge/Parquet-zstd-50ABF1)

---

## Architecture

```mermaid
flowchart LR
    A[Riot API] -->|async scraper| B[(SQLite)]
    B --> C{{Quality gate<br/>source}}
    C -->|extract| D[(Parquet lake<br/>zstd, partitioned)]
    D -->|COPY + upsert| E[(Postgres<br/>raw schema)]
    E --> F{{Quality checks<br/>warehouse}}
    F --> G[dbt staging<br/>views]
    G --> H[dbt marts<br/>tables + tests]
    H --> I[Streamlit dashboard]
    J[Airflow DAG] -. schedules .-> C
```

The scraper (Clean Architecture: domain / application / infrastructure / presentation) writes to SQLite. The `pipeline/` package turns that into tested analytics tables.

## Features

**Scraper**
- Ranked Solo/Duo and Flex 5v5 matches across all major Riot servers
- Patch-aware and date-window filtering
- Async fetching with per-endpoint rate limiting
- Seeding from high-elo leagues, existing DB players, or your own PUUIDs
- Crash-safe: sessions resume from the region where a run stopped
- Structured JSON logging, health checks, desktop notifications

**Pipeline**
- **Extract:** SQLite to Parquet (zstd), explicit Arrow schemas, batched reads, `matches` partitioned by `patch_version`
- **Load:** Parquet to Postgres via `COPY` into a temp table, then `INSERT ... ON CONFLICT DO UPDATE`. Idempotent, one transaction, row-count reconciliation, `raw._load_audit` table
- **Quality:** 15 SQL checks (`error` stops the run, `warn` is reported) run on the source and again on the warehouse, plus row-count regression detection between runs
- **dbt:** 5 staging views, 4 marts, 24 tests. Player ids are md5-hashed in staging
- **Orchestration:** Airflow DAG with retries, `max_active_runs=1`, quality gates between steps
- **CI:** lint, tests with a Postgres service, full pipeline run on synthetic data, Docker builds

## Quick start

### 1. Install

```bash
pip install -r requirements.txt -r requirements-pipeline.txt -r requirements-dev.txt
```

### 2. Start Postgres

```bash
docker compose up -d postgres
```

Or point the `PG*` variables (see `.env.example`) at any Postgres 14+ instance.

### 3. Run the pipeline

```bash
# No Riot API key? Generate synthetic data first:
python -m pipeline.cli make-sample --matches 300

# Quality gate > extract > load > verify > dbt build
python -m pipeline.cli run-all

# Explore the results
streamlit run dashboard/app.py
```

### Individual steps

| Command | What it does |
|---|---|
| `python -m pipeline.cli check-source` | Quality checks on the SQLite source |
| `python -m pipeline.cli extract` | SQLite to Parquet lake |
| `python -m pipeline.cli load [--mode upsert\|replace]` | Parquet to Postgres `raw` schema |
| `python -m pipeline.cli check-warehouse` | Quality checks on Postgres |
| `python -m pipeline.cli dbt-build` | dbt run + test |
| `python -m pipeline.cli run-all [--skip-dbt]` | Everything above, in order |

Shortcuts for all of these are in the `Makefile` (`make pipeline`, `make test`, `make lint`, ...).

### Docker

```bash
docker compose --profile batch run --rm pipeline     # one-off full run
docker compose --profile airflow up                  # Airflow UI on :8080
docker compose --profile dashboard up                # Streamlit on :8501
```

## Running the scraper

1. Create `config/.env`:
   ```
   RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```
2. Run it:
   ```bash
   TARGET_PATCH="16.3" MATCHES_PER_REGION="2500" python -u main.py
   ```
3. Choose from the menu: full scrape, targeted single-server scrape, health check, DB check, notifications.

Main scraper settings (environment variables):

| Variable | Default | Description |
|---|---|---|
| `RIOT_API_KEY` | none (required) | Riot developer API key |
| `TARGET_PATCH` | `16.3` | Patch to collect, e.g. `16.3` or `16` |
| `PATCH_START_DATE` | `2026-02-05` | Lower bound of the patch date window |
| `MATCHES_PER_REGION` | per `settings.py` | Target matches per server |
| `MAX_CONCURRENT_REQUESTS` | `16` | Async concurrency limit |
| `SEED_PUUIDS` / `SEED_SUMMONERS` | none | Extra seed players |
| `REGIONS` / `DISABLED_REGIONS` | none | Limit or skip servers |

Pipeline settings:

| Variable | Default | Description |
|---|---|---|
| `WAREHOUSE_DSN` | built from `PG*` | Full Postgres connection string |
| `PGHOST` `PGPORT` `PGUSER` `PGPASSWORD` `PGDATABASE` | `localhost` `5432` `lol` `lol` `lol` | Postgres connection |
| `LOL_SQLITE_PATH` | `data/db/scraper.sqlite` | Source database |
| `LOL_LAKE_DIR` | `data/lake` | Parquet output |
| `LOL_REPORT_DIR` | `data/reports` | Quality report JSON |

## Data model

**Raw tables** (mirror of the scraper output): `matches`, `teams`, `participants`, `participant_items`, `participant_summoner_spells`, `champions`, `items`, `summoner_spells`, `platforms`.

**dbt models**

| Model | Grain | Notes |
|---|---|---|
| `stg_*` | 1:1 with raw | Types, naming, `is_remake` flag, hashed `player_key` |
| `fct_participant_match` | player x match | KDA, gold/min, damage/min, team damage share |
| `mart_champion_performance` | patch x queue x champion x role | Win rate, pick rate, averages, `is_reliable_sample` (30+ games). Remakes excluded |
| `mart_item_popularity` | patch x queue x item | Build count and win rate |
| `mart_region_summary` | patch x region x queue | Match counts, median duration, detail coverage |

## Data quality checks

| Check | Severity |
|---|---|
| Required fields present on matches | error |
| Positive game duration | error |
| Valid `team_id` (100 or 200) | error |
| No orphan teams or participants | error |
| Exactly 10 participants per match | error |
| Exactly one winning team per match | error |
| Participant `win` agrees with team `win` | error |
| Non-negative kills, deaths, assists, gold | error |
| Champions exist in the reference table | error |
| One row per player per match | error |
| Items exist in the reference table | warn |
| Games under 3 minutes (remakes) | warn |
| Matches without participant detail | warn |
| `rank_tier` carries more than one value | warn |

Reports are written to `data/reports/quality_source.json` and `quality_warehouse.json`.

## Known limitations of the bundled data

Running the checks on the database shipped with the repo shows:

- 40,385 matches are stored, but only 901 (2.2%) have participant and team rows. The last scrape session is still marked `running`, so it looks like an interrupted run. Finishing a scrape fills the gap.
- `rank_tier` is `UNRANKED` for every participant, so the column carries no signal.
- 587 matches are shorter than 3 minutes (remakes). They are flagged and excluded from champion and item statistics.

## Testing

```bash
pytest                                                              # unit tests
WAREHOUSE_DSN=postgresql://lol:lol@localhost:5432/lol pytest        # plus Postgres integration tests
ruff check pipeline dashboard orchestration tests/pipeline          # lint
```

79 tests: 57 for the scraper and 22 for the pipeline (schema, extract, quality, Postgres load).

## Project structure

```
.
├── config/                  # settings and .env
├── domain/                  # entities, enums, interfaces
├── application/             # scraping, seeding, persistence services
├── infrastructure/          # Riot client, repositories, health checks
├── presentation/cli/        # console commands
├── core/logging/            # structured logging
├── pipeline/                # extract, load, quality, CLI, sample data
├── dbt_lol/                 # dbt project (staging, marts, tests)
├── orchestration/dags/      # Airflow DAG
├── dashboard/app.py         # Streamlit dashboard
├── docker/                  # Dockerfiles
├── docker-compose.yml
├── .github/workflows/ci.yml
├── tests/
└── main.py                  # scraper entry point
```

## Design decisions

- **Postgres plus dbt on top of SQLite:** the scraper keeps SQLite (zero ops, single writer). Analytics gets a real warehouse for SQL transformations and tests. Moving to Snowflake or BigQuery means a new loader and a dbt adapter, not a rewrite.
- **Parquet in the middle:** decouples extract from load, makes loads replayable, and matches the layout you would use in S3 or GCS. The partition column is typed as a string so patch `16.10` is never read as `16.1`.
- **Raw stays faithful:** pseudonymisation of player identifiers happens in staging, so raw is an exact copy of the source.
- **Full re-extract each run:** simple and correct at this size. For larger data, extract incrementally by a `game_creation` watermark. The loader's upsert already supports it.
- **dbt in its own virtualenv inside the Airflow image:** avoids dependency conflicts with Airflow's pinned packages.

## Credits and license

Analytics pipeline (Parquet lake, Postgres loader, dbt models, data quality checks, Airflow DAG, Docker, CI and dashboard) built by **Appu**.

The underlying Riot API scraper is based on the open-source project by Mohamed Darwish.

For educational and data engineering purposes only. Not affiliated with or endorsed by Riot Games.

