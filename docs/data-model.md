# Data model

## Medallion
- **bronze** — `yellow_tripdata_raw`, `green_tripdata_raw`: faithful to source + a `source_file` column.
- **silver** — `taxi_trips`: yellow+green unified, canonical timestamps, typed, `is_amount_valid` flag. **Spark SQL, pure conformation — no filter** (every month and row kept). **Liquid Clustered by `(year, month)`**, parsed from the file name during conformation (deterministic, immune to stray row dates). Carries `year`/`month` + `_source_version`; **`source_file` is not propagated past bronze**.
- **gold** — `obt_trips` (Spark SQL): a join-free consumption table — consumption columns + derived `year`/`month`/`pickup_hour`, Liquid Clustered by `(year, month)`. **No scope filter**; the Jan–May 2023 scope + question rules live in `analysis/`. Source of the answers.

Both silver and gold are loaded **incrementally via Delta Change Data Feed** (read only the source's new commits), with a `_source_version` watermark column. See the runbook's *How it works*.

Observability via Delta history (`DESCRIBE HISTORY`). Per-row lineage: `source_file` (bronze only) and `_source_version` (the CDF source version on silver/gold), plus Delta history (which already records each load's commit time).

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
- **Ingestion scope:** download lands 2023-01 to the latest published month (both taxis); the TLC publishes whole closed months with ~2 months' lag, and unpublished months return 403/404 and are skipped. The **consumption scope (Jan–May 2023)** is applied in `analysis/answers.sql`, not at ingestion and not in the tables.
- **Canonical timestamps:** yellow `tpep_*`, green `lpep_*` → `pickup_datetime`/`dropoff_datetime` in silver.
- **Negative total_amount kept** (refund/void = real revenue; payment_type 4/6). Flag `is_amount_valid`, don't filter.
- **OBT (no full star):** the 2 questions are simple aggregates, so a single denormalized `obt_trips` serves them join-free. A star (fact + dimensions) would add tables the case doesn't need.
- **`source_file` in bronze only.** It is the bronze ingestion idempotency key (append, deduped by name — one file lands once), the source of `year`/`month` (parsed from the name), and fine-grained row→file lineage. Silver/gold derive `year`/`month` from it during conformation but don't persist it; they carry `year`/`month` + `_source_version`. Reverse lookup when needed: `_source_version` locates the bronze commit, where `source_file` lives.
- **Silver/gold idempotency:** incremental via **Delta Change Data Feed**. Each target reads only its source's new commits (`readChangeFeed` from `watermark + 1`), bootstrapping with a full read on the first run; reruns with no new commits are no-ops. The watermark is a `_source_version` column (= the source Delta version each row came from); `max(_source_version)` is the resume point — one per `taxi_type` in silver (yellow/green are separate tables), one in gold. This replaced the earlier `source_file not in (...)` anti-join, which full-scanned the source.
- **Validation, fail-fast:** row-count reconciliation per period `(year, month)` (bronze↔silver, silver↔gold) plus value asserts. Reconciling by period (not by `source_file`) is the trade-off for dropping `source_file` from silver — `taxi_type` narrows it, and bronze still has the per-file detail.

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
- **Lineage?** `source_file` per row in bronze (fine-grained row→file) and `_source_version` on silver/gold (the CDF source version), plus Delta history (which records each load's commit). To trace a silver/gold row to its file, `_source_version` points at the bronze commit.

## Scale notes
- **Incremental reads** are Delta-native: silver/gold consume only their source's new commits via
  Change Data Feed (`readChangeFeed` from the `_source_version` watermark), so a run touches only newly
  appended data, not the whole source. This scales with the *delta*, not the table size.
- **Physical layout** lives on the query surfaces (silver/gold), Liquid Clustered by `(year, month)` for
  period-filtered reads. Bronze stays raw append; if anything it would be partitioned by *ingest date*
  for file management, never by trip period.
- **Bootstrap:** the first load of a target full-reads the source (no CDF history yet) and sets the
  watermark to the source's current version; every later run is pure CDF.
