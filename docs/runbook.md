# Runbook

## Current state
- **Step 1 — setup** (PR #1): scaffolding, `config.py` (`CATALOG`, `get_spark`, `get_logger`,
  `run_sql_file`), `00_setup.sql`/`.py`. Catalog/schemas/volume carry comments + tags. Dev/prod
  isolated by catalog via `NYC_TLC_CATALOG`.
- **Step 2 — extract + bronze** (PRs #12/#14, CDF added in #18): `01_download.py` lands TLC parquet
  incrementally (unpublished months 403/404 are skipped), `02_bronze.py` appends new files into
  `bronze.{yellow,green}_tripdata_raw` (only files whose `source_file` isn't there yet; the atomic
  append keeps reruns idempotent), with Change Data Feed enabled (version 0) for the silver/gold
  incremental; `03_verify.py` reconciles landing vs bronze row counts (fail-fast).
- **Step 3 — silver** (PR #15, reworked in Step 4 / #19): `04_silver` conforms yellow+green into
  `silver.taxi_trips`. The original `source_file not in (...)` anti-join (a full scan) was replaced by
  incremental **Delta CDF** with a `_source_version` watermark per `taxi_type`; `05_verify.py`
  reconciles bronze↔silver counts (see How it works).
- **Step 4 — gold + analysis** (this PR): `06_gold` conforms the silver CDF into `gold.obt_trips`
  (a join-free OBT: consumption columns + derived `year`/`month`/`pickup_hour`, single watermark, no
  scope filter); `07_verify.py` reconciles silver↔gold counts; `analysis/answers.sql` answers the 2
  questions with the Jan–May 2023 scope applied there.
- Merge to `main` auto-deploys to prod via the GitHub Actions `deploy` job (temporary bridge, retired in Step 5).

## Plan (one PR per phase)
- Step 1 — setup. ✅
- Step 2 — extract + bronze. ✅
- Step 3 — silver (conform). ✅
- **Step 4 — CDF incremental rework + gold + analysis** (in progress, sliced into PRs):
  - **Bronze CDF** (PR #18 ✅): `delta.enableChangeDataFeed` from creation (version 0); ingested rows
    logged via Delta history; `reset.py` added to drop the catalog for a clean re-test.
  - **Silver CDF** (this PR): `04_silver.sql` DDL gains `_source_version` and drops `source_file`
    (CDF on, clustered by `(year, month)`); `04_silver_conform.sql` conforms a bronze CDF batch in
    Spark SQL over a temp view; `04_silver.py` runs it incrementally (watermark = `max(_source_version)`
    per `taxi_type`); `05_verify.py` reconciles bronze↔silver row counts per `taxi_type`. Shared CDF
    helpers in `config.py` (`last_version`, `table_version`, `read_inserts_since`).
  - **Gold + analysis** (this PR): `06_gold.*` builds `gold.obt_trips` (consumption columns + derived
    `year`/`month`/`pickup_hour`, Liquid Clustered by `(year, month)`, **no scope filter**, no CDF — it's
    the serving layer); single watermark (silver is the only source); `07_verify.py` reconciles
    silver↔gold; `analysis/answers.sql` holds the 2 queries with the Jan–May 2023 scope applied here.
- Step 5 — orchestration (Asset Bundle / Databricks Job; retire the Actions deploy bridge).
- Step 6 — readme + eda polish.
- Step 7 — final review + delivery.

## How it works
A medallion over the NYC TLC dataset, incremental at every hop.

1. **Layers.** Bronze = raw source + `source_file` (faithful, schema-on-read). Silver = conformed
   yellow+green (canonical pickup/dropoff timestamps, typed columns, `is_amount_valid` flag).
   Gold = `obt_trips`, a join-free consumption table (consumption columns + derived
   `year`/`month`/`pickup_hour`).
2. **Delta-native incremental (CDF).** Bronze and silver have `delta.enableChangeDataFeed = true` from
   creation (version 0); gold does not (it's the serving layer, nothing reads its feed). Silver and gold
   read only the *new commits* of their source via `readChangeFeed` (`startingVersion = watermark + 1`),
   never the whole table. The first run has `watermark = -1`, so it reads the feed from version 0: a
   single code path, no separate full-read bootstrap.
3. **Watermark.** Each target row carries `_source_version` = the Delta version of the source commit
   it came from; the watermark is `max(_source_version)`. Silver keeps one watermark per `taxi_type`
   (yellow and green are separate Delta tables with independent histories); gold keeps one (silver is
   its only source). `source_file` stays in bronze (ingestion idempotency + the `year`/`month` source);
   silver/gold carry `year`/`month` + `_source_version`, not `source_file`.
4. **Idempotency.** Bronze appends only files whose `source_file` isn't already there, and the append
   is one atomic commit (a failure lands the batch fully or not at all, never duplicates); the bronze
   table itself is the source of truth for what's ingested. Silver/gold reruns are no-ops too: with no
   new commits the CDF read returns nothing, so nothing is appended.
5. **Validation (fail-fast).** Silver reconciles row counts per `taxi_type` against bronze
   (`05_verify.py`): conformation is 1:1, so they must match. Counts use `count(*)` (metadata-only on
   bronze) and the low-cardinality `taxi_type` column, not a full scan. Gold reconciles against silver
   the same way (`07_verify.py`).
6. **Business scope** (Jan–May 2023 + question rules) lives in `analysis/`, not in the tables, so the
   layers stay general and reusable.
7. **Observability.** Delta history records every load; `source_file` (bronze) and `_source_version`
   (silver/gold) give per-row lineage. No control schema.

## Checklist
1. Download + bronze yellow & green. ✅
2. Consumption layer with required columns + taxi_type + is_amount_valid. (silver ✅ / gold ✅)
3. PySpark in ingestion. ✅
4. Gold OBT (join-free). ✅
5. Both questions answered. ✅ (`analysis/answers.sql`)
6. Observability: Delta history + lineage. ✅
7. Job DAG versioned. — Step 5
8. README with run steps + rationale. — Step 6

## Tech debt (after delivery)
1. **Trim comments — lighter, less AI-sounding.** Review the SQL/Python comments (notably the
   `04_silver.sql` header and the `02_bronze.py` docstring): keep what guides the reader, drop the rest.
