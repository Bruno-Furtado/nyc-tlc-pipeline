# Runbook

## Current state
- **Step 1 — setup** (PR #1): scaffolding, `config.py` (`CATALOG`, `get_spark`, `get_logger`,
  `run_sql_file`), `00_setup.sql`/`.py`. Catalog/schemas/volume carry comments + tags. Dev/prod
  isolated by catalog via `NYC_TLC_CATALOG`.
- **Step 2 — extract + bronze** (PRs #12/#14): `01_download.py` lands TLC parquet incrementally
  (unpublished months 403/404 are skipped), `02_bronze.py` appends new files into
  `bronze.{yellow,green}_tripdata_raw` (deduped by `source_file`), `03_verify.py` reconciles
  landing vs bronze row counts (fail-fast).
- **Step 3 — silver** (PR #15): `04_silver.sql`/`.py` conform yellow+green into `silver.taxi_trips`.
  > Reworked in Step 4: today's `source_file not in (...)` incremental full-scans bronze; moving to
  > Delta CDF (see How it works).
- Merge to `main` auto-deploys to prod via the GitHub Actions `deploy` job (temporary bridge, retired in Step 5).

## Plan (one PR per phase)
- Step 1 — setup. ✅
- Step 2 — extract + bronze. ✅
- Step 3 — silver (conform). ✅
- **Step 4 — gold + analysis + CDF incremental rework** (next):
  - **Bronze:** enable `delta.enableChangeDataFeed` (stays raw — no derived columns, no clustering).
  - **Silver + gold:** incremental by **Delta Change Data Feed + a `_source_version` watermark column**,
    replacing the `source_file not in (...)` anti-join. Shared helpers live in `config.py`
    (`table_version`, `read_inserts_since`, `last_version`, `reconcile_counts`, `assert_no_rows`).
  - **Gold** (`05_gold.sql`/`05_gold_conform.sql`/`05_gold.py`): build `gold.obt_trips` —
    consumption columns + derived `year`/`month`/`pickup_hour`, Liquid Clustered by `(year, month)`,
    **no scope filter**.
  - **Silver runner** (`04_silver.py` + `04_silver_conform.sql`): DDL gains `_source_version`; runner
    reads each bronze table's new commits, conforms (Spark SQL over a temp view), appends.
  - **Validation** in silver + gold: per-key count reconciliation + value asserts (fail-fast).
  - **Analysis** (`analysis/answers.sql`): the 2 queries, with the Jan–May 2023 scope applied here.
- Step 5 — orchestration (Asset Bundle / Databricks Job; retire the Actions deploy bridge).
- Step 6 — readme + eda polish.
- Step 7 — final review + delivery.

## How it works
A medallion over the NYC TLC dataset, incremental at every hop.

1. **Layers.** Bronze = raw source + `source_file` (faithful, schema-on-read). Silver = conformed
   yellow+green (canonical pickup/dropoff timestamps, typed columns, `is_amount_valid` flag).
   Gold = `obt_trips`, a join-free consumption table (consumption columns + derived
   `year`/`month`/`pickup_hour`).
2. **Delta-native incremental (CDF).** Bronze has `delta.enableChangeDataFeed = true`. Silver and
   gold read only the *new commits* of their source via `readChangeFeed`
   (`startingVersion = watermark + 1`), never the whole table. The first run bootstraps with a full
   read of the source at its current version.
3. **Watermark.** Each target row carries `_source_version` = the Delta version of the source commit
   it came from; the watermark is `max(_source_version)`. Silver keeps one watermark per `taxi_type`
   (yellow and green are separate Delta tables with independent histories); gold keeps one (silver is
   its only source).
4. **Idempotency.** Reruns are no-ops: with no new commits the CDF read returns nothing, so nothing
   is appended.
5. **Validation (fail-fast).** Count reconciliation per key (bronze↔silver by `source_file`,
   silver↔gold by `(year, month)`) plus value asserts (e.g. non-null timestamps, `pickup_hour` in 0–23).
6. **Business scope** (Jan–May 2023 + question rules) lives in `analysis/`, not in the tables, so the
   layers stay general and reusable.
7. **Observability.** Delta history records every load; `source_file` and `_source_version` give
   per-row lineage. No control schema.

## Checklist
1. Download + bronze yellow & green. ✅
2. Consumption layer with required columns + taxi_type + is_amount_valid. (silver ✅ / gold Step 4)
3. PySpark in ingestion. ✅
4. Gold OBT (join-free). — Step 4
5. Both questions answered. — Step 4 (`analysis/`)
6. Observability: Delta history + lineage. ✅
7. Job DAG versioned. — Step 5
8. README with run steps + rationale. — Step 6

## Tech debt (after delivery)
1. **Trim comments — lighter, less AI-sounding.** Review the SQL/Python comments (notably the
   `04_silver.sql` header and the `02_bronze.py` docstring): keep what guides the reader, drop the rest.
