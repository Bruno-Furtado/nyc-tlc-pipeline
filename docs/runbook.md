# Runbook

## Current state
Setup phase ready (pending its PR): scaffolding (`.gitignore`, `ruff.toml` with E/F/I/ANN,
pre-commit hook that blocks direct commits to `main` and runs ruff, `.vscode`), `config.py`
(`CATALOG`, `get_spark()`, `get_logger()`), `00_setup.sql` + `00_setup.py` runner, docs and README.
Dev/prod isolated by catalog via `NYC_TLC_CATALOG` (default `nyc_tlc_dev`).
Merge to `main` auto-deploys to prod (`nyc_tlc`): the `deploy` job in `ci.yml` runs every
`src/pipeline/NN_*.py` in order via Databricks Connect (needs `DATABRICKS_HOST`/`DATABRICKS_TOKEN`
secrets). Step 5 (Asset Bundle Job DAG) is the more robust orchestration that supersedes this later.

## Plan (one PR per phase)
- **Step 1 — setup:** scaffolding + `config.py` (`CATALOG`, `get_spark()`, `get_logger()`) + `00_setup.sql`/`00_setup.py` (catalog, bronze/silver/gold schemas, landing volume).
- **Step 2 — extract + bronze:** `01_download.py` (TLC → volume via SDK Files API), `02_bronze.py` (parquet → bronze delta + audit cols: audit_id, ingestion_timestamp, source_file).
- **Step 3 — silver:** `03_silver.py` — normalize tpep_/lpep_ → canonical timestamps, union yellow+green, type, `is_amount_valid` flag, derive pickup_hour/year/month. Partition by year/month.
- **Step 4 — gold + analysis:** `04_gold.py` (dim_date, dim_vendor, dim_taxi_type, fact_trips, obt_trips) + `analysis/answers.sql` and `eda.ipynb`.
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
