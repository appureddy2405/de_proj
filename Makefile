.PHONY: install sample check extract load quality dbt pipeline test lint up down dashboard

PY ?= python

install:           ## install scraper + pipeline + dev dependencies
	$(PY) -m pip install -r requirements.txt -r requirements-pipeline.txt -r requirements-dev.txt

sample:            ## create a synthetic SQLite DB (no Riot API key needed)
	$(PY) -m pipeline.cli make-sample --matches 300

check:             ## data quality gate on the SQLite source
	$(PY) -m pipeline.cli check-source

extract:           ## SQLite -> Parquet lake
	$(PY) -m pipeline.cli extract

load:              ## Parquet lake -> Postgres raw schema
	$(PY) -m pipeline.cli load

quality:           ## data quality checks on the Postgres raw schema
	$(PY) -m pipeline.cli check-warehouse

dbt:               ## dbt run + test (staging and marts)
	$(PY) -m pipeline.cli dbt-build

pipeline:          ## everything: gate > extract > load > verify > dbt
	$(PY) -m pipeline.cli run-all

test:
	$(PY) -m pytest

lint:
	ruff check pipeline dashboard orchestration tests/pipeline

up:                ## start Postgres in Docker
	docker compose up -d postgres

down:
	docker compose down

dashboard:
	streamlit run dashboard/app.py
