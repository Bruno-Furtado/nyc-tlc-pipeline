# Runbook

## Current state
Setup phase merged (PR #1): scaffolding (`.gitignore`, `ruff.toml` with E/F/I/ANN, pre-commit hook
that blocks direct commits to `main` and runs ruff, `.vscode`), `config.py` (`CATALOG`,
`get_spark()` on serverless, `get_logger()`), `00_setup.sql` + `00_setup.py` runner. Catalog objects
carry comments + tags (see data-model.md). Dev/prod isolated by catalog via `NYC_TLC_CATALOG`
(default `nyc_tlc_dev`).
Merge to `main` auto-deploys to prod (`nyc_tlc`): the `deploy` job in `ci.yml` runs every
`src/pipeline/NN_*.py` in order via Databricks Connect (needs `DATABRICKS_HOST`/`DATABRICKS_TOKEN`
secrets). **This GitHub Actions deploy is a temporary bridge** — it reuses the same code we run
locally to get auto-deploy with zero extra setup, but prod's real home is a Databricks Job (see Step 5).

Extract + bronze done (Step 2): `01_download.py` lands TLC parquet into `bronze.landing/{taxi}`
incrementally (only missing months; unpublished months 403/404 are skipped), `02_bronze.py` appends new
files into `bronze.{yellow,green}_tripdata_raw` Delta with a `source_file` column, deduped by
`source_file`. Tables carry comments + tags.
`03_verify.py` reconciles row counts per `source_file` (landing vs bronze) and fails fast on any mismatch,
so a broken ingestion stops the deploy.

Silver done (Step 3): `04_silver.sql` (run by the thin `04_silver.py` via `config.run_sql_file`) builds
`silver.taxi_trips` — union yellow+green, canonical `pickup_datetime`/`dropoff_datetime`, typed columns
(`vendor_id`, `passenger_count`, `total_amount`), `taxi_type`, `is_amount_valid` flag, plus `year`/`month`
from the file name. **Incremental by `source_file`** (`create table if not exists` + `insert ... where
source_file not in (silver)`), **Liquid Clustered by `(year, month)`**. Pure conformation in **Spark SQL**,
no filter; scope and rules are deferred to the gold OBT.

## Plan (one PR per phase)
- **Step 1 — setup:** scaffolding + `config.py` (`CATALOG`, `get_spark()`, `get_logger()`) + `00_setup.sql`/`00_setup.py` (catalog, bronze/silver/gold schemas, landing volume).
- **Step 2 — extract + bronze:** `01_download.py` (TLC → volume via SDK Files API, incremental from 2023-01 to latest published month), `02_bronze.py` (parquet → bronze delta, append deduped by source_file), `03_verify.py` (reconcile landing vs bronze row counts per source_file, fail-fast on mismatch).
- **Step 3 — silver:** `04_silver.sql` (run by `04_silver.py`) — union yellow+green, canonical timestamps (tpep_/lpep_ → pickup_datetime/dropoff_datetime), typed, `is_amount_valid` flag. **Pure conformation, no filter** — every month and row is kept; the Jan–May 2023 scope and the question rules live in the gold OBT. Built in **Spark SQL** (consumption language is free); PySpark stays in ingestion.
- **Step 4 — gold + analysis:** `05_gold.sql` (OBT: applies the Jan–May 2023 scope + rules + derived year/month/hour, source of the answers) + `analysis/answers.sql` and `eda.ipynb`.
- **Step 5 — orchestration:** replace the GitHub Actions `deploy` job (the Databricks Connect bridge) with a Databricks Job DAG defined as an **Asset Bundle** (`databricks.yml`), versioned in the repo. Tasks `setup → download → bronze → verify → silver → gold` run **inside** the workspace (driver downloads straight to the volume; workspace identity instead of a GitHub token), on a **monthly schedule** (picks up newly published TLC months), with per-task retries and failure alerts, params by range/type. CI keeps lint on PRs; the `deploy` job is retired here.
- **Step 6 — readme + eda polish.**
- **Step 7 — final review + delivery.**

## Checklist
1. Download in Databricks + bronze yellow & green.
2. Consumption layer with the required columns + taxi_type + is_amount_valid.
3. PySpark in ingestion.
4. Gold: OBT (consumption, join-free).
5. Both questions answered.
6. Observability: Delta history + `source_file` lineage.
7. Job DAG versioned.
8. README with run steps + rationale.
