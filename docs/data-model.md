# Data model

## Medallion
- **bronze** — `yellow_tripdata_raw`, `green_tripdata_raw`: faithful to source + a `source_file` column.
- **silver** — `taxi_trips`: yellow+green unified, canonical timestamps, typed, `is_amount_valid` flag. **Spark SQL, pure conformation — no filter** (every month and row kept). **Incremental by `source_file`**; **Liquid Clustered by `(year, month)`** taken from the file name (deterministic, immune to stray row dates).
- **gold** — `obt_trips` (Spark SQL): the consumption table that applies the Jan–May 2023 scope + question rules + derived `year`/`month`/`hour`, and is the source of the answers.

Observability via Delta history (`DESCRIBE HISTORY`). Load lineage via `source_file` on each row, plus Delta history (which already records each load's commit time).

## Metadata (comments & tags)
Every Unity Catalog object carries metadata — set in `00_setup.sql` for catalog/schemas/volume,
and on tables and key columns as each layer is built. Both surface in **Catalog Explorer** and feed
**AI/BI Genie**, so they're descriptive and business-oriented (Databricks standard practice).

- **Comments** — `COMMENT ON … IS …` (not inline `CREATE … COMMENT`): idempotent, reapplies to
  existing objects, while `CREATE IF NOT EXISTS` skips them.
- **Tags** — `ALTER … SET TAGS (…)` (idempotent): `project = nyc-tlc` on the catalog, `layer =
  bronze|silver|gold` on the schemas; later for column-level classification (e.g. PII). Note:
  `SET TAGS` rejects `IDENTIFIER(:catalog || '.<schema>')`, so we `USE CATALOG identifier(:catalog)`
  first and tag schemas by relative name.

`config.run_sql_file` strips `--` line comments before splitting on `;`, but a `;` inside a string
literal still splits — so keep `COMMENT`/`SET TAGS` text free of `;`.

## Decisions
- **Yellow + green only** (NYC taxis; FHV/HVFHV aren't taxis, no passenger_count). Q1 = yellow; Q2 = yellow+green.
- **Ingestion scope:** download lands 2023-01 to the latest published month (both taxis); the TLC publishes whole closed months with ~2 months' lag, and unpublished months return 403/404 and are skipped. The **consumption scope (Jan–May 2023)** is applied in the gold OBT, not at ingestion.
- **Canonical timestamps:** yellow `tpep_*`, green `lpep_*` → `pickup_datetime`/`dropoff_datetime` in silver.
- **Negative total_amount kept** (refund/void = real revenue; payment_type 4/6). Flag `is_amount_valid`, don't filter.
- **OBT (no full star):** the 2 questions are simple aggregates, so a single denormalized `obt_trips` serves them join-free. A star (fact + dimensions) would add tables the case doesn't need.
- **Bronze idempotency:** append incremental, deduped by `source_file` (one file lands once). Lineage is `source_file` per row; the load itself is recorded in Delta history (no separate audit_id/ingestion_timestamp columns).
- **Silver idempotency:** incremental by `source_file` — `create table if not exists` then `insert ... where source_file not in (silver)`, so only new files are added. Liquid Clustered by `(year, month)` from the file name.

## Queries
```sql
-- Q1: avg total_amount per month, yellow only
select year, month, round(avg(total_amount), 2) as avg_total_amount
from nyc_tlc.gold.obt_trips
where taxi_type = 'yellow'
group by year, month
order by year, month;

-- Q2: avg passengers per hour, May 2023, all taxis
select pickup_hour, round(avg(passenger_count), 2) as avg_passengers
from nyc_tlc.gold.obt_trips
where year = 2023 and month = 5 and passenger_count > 0
group by pickup_hour
order by pickup_hour;
```

## FAQ
- **Why medallion?** Auditing, reprocessing, engineering/analytics separation.
- **Why Delta?** ACID, idempotent MERGE, schema enforcement, time travel.
- **Why OBT (not a star)?** The 2 questions are simple aggregates; one denormalized OBT serves them join-free. A star adds dimensions the case doesn't need.
- **Negative amounts?** Refund/void is real revenue; filtering biases the average.
- **Lineage?** `source_file` on each row, plus Delta history (which records each load's commit).

## Scale notes
The dataset is small, so the pipeline favours simplicity. At larger scale:
- **Physical layout** lives on the query surfaces (silver/gold), not bronze — bronze is raw append, read
  wholesale by the silver incremental. Silver is Liquid Clustered by `(year, month)`; the gold OBT would
  be too. Bronze, if anything, would be partitioned by *ingest date* for file management, never by trip period.
- **Incremental reads:** `where source_file not in (...)` is a logical incremental (only new files are
  written) but a dynamic anti-join, so it still scans bronze — negligible at this size. True read pruning
  needs a *static* partition filter: compute the new periods in the driver and issue literal
  `where year=… and month=…` inserts against a period-partitioned bronze, or use Structured Streaming /
  Delta Change Data Feed. Documented rather than built, since it adds no benefit at this volume.
