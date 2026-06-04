# Runbook

## Current state
Setup phase merged (PR #1): scaffolding (`.gitignore`, `ruff.toml` with E/F/I/ANN, pre-commit hook
that blocks direct commits to `main` and runs ruff, `.vscode`), `config.py` (`CATALOG`,
`get_spark()` on serverless, `get_logger()`), `00_setup.sql` + `00_setup.py` runner. Catalog objects
carry comments + tags (see data-model.md). Dev/prod isolated by catalog via `NYC_TLC_CATALOG`
(default `nyc_tlc_dev`).
Merge to `main` auto-deploys to prod (`nyc_tlc`): the `deploy` job in `ci.yml` runs every
`src/pipeline/NN_*.py` in order via Databricks Connect (needs `DATABRICKS_HOST`/`DATABRICKS_TOKEN`
secrets). Step 5 (Asset Bundle Job DAG) is the more robust orchestration that supersedes this later.

Extract + bronze in progress (Step 2): `01_download.py` lands TLC parquet into `bronze.landing/{taxi}`
incrementally (only missing months; unpublished months 403/404 are skipped), `02_bronze.py` appends new
files into `bronze.{yellow,green}_tripdata_raw` Delta with audit columns (`audit_id` per run,
`ingestion_timestamp`, `source_file`), deduped by `source_file`. Tables carry comments + tags.
`03_verify.py` reconciles row counts per `source_file` (landing vs bronze) and fails fast on any mismatch,
so a broken ingestion stops the deploy.

## Plan (one PR per phase)
- **Step 1 — setup:** scaffolding + `config.py` (`CATALOG`, `get_spark()`, `get_logger()`) + `00_setup.sql`/`00_setup.py` (catalog, bronze/silver/gold schemas, landing volume).
- **Step 2 — extract + bronze:** `01_download.py` (TLC → volume via SDK Files API, incremental from 2023-01 to latest published month), `02_bronze.py` (parquet → bronze delta, append deduped by source_file + audit cols: audit_id per run, ingestion_timestamp, source_file), `03_verify.py` (reconcile landing vs bronze row counts per source_file, fail-fast on mismatch).
- **Step 3 — silver:** `04_silver.py` — normalize tpep_/lpep_ → canonical timestamps, union yellow+green, type, `is_amount_valid` flag, derive pickup_hour/year/month. Use Liquid Clustering (year/month) over Hive partitioning. **Open: evaluate dbt** for silver/gold (SQL models + `dbt test`) — fits the star schema, but adds tooling; decide when starting this step.
- **Step 4 — gold + analysis:** `05_gold.py` (dim_date, dim_vendor, dim_taxi_type, fact_trips, obt_trips) + `analysis/answers.sql` and `eda.ipynb`.
- **Step 5 — orchestration:** Databricks Job DAG (Asset Bundle), params by range/type.
- **Step 6 — readme + eda polish.**
- **Step 7 — final review + delivery.**

## Checklist
1. Download in Databricks + bronze yellow & green.
2. Consumption layer with the required columns + taxi_type + is_amount_valid.
3. PySpark in ingestion.
4. Gold: star schema + OBT.
5. Both questions answered.
6. Observability: audit_id + Delta history.
7. Job DAG versioned.
8. README with run steps + rationale.
