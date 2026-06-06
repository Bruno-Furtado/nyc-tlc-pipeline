# Data model

## Medallion
- **bronze** — `yellow_tripdata_raw`, `green_tripdata_raw`: faithful to source + a `source_file` column; **Change Data Feed enabled** so silver reads only the new commits.
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

`config.run_sql_file` splits each file on `;`, so keep `;` out of comments and out of
`COMMENT`/`SET TAGS` text (a stray `;` in either splits a statement and breaks parsing).

## Decisions
- **Yellow + green only** (NYC taxis; FHV/HVFHV aren't taxis, no passenger_count). Q1 = yellow; Q2 = yellow+green.
- **Ingestion scope:** download lands 2023-01 to the latest published month (both taxis) by default, overridable per run via `NYC_TLC_START`/`NYC_TLC_END` (`YYYY-MM`); the TLC publishes whole closed months with ~2 months' lag, and unpublished months return 403/404 and are skipped. The **consumption scope (Jan–May 2023)** is applied in the `analysis/` queries (one `.sql` per question), not at ingestion and not in the tables.
- **Canonical timestamps:** yellow `tpep_*`, green `lpep_*` → `pickup_datetime`/`dropoff_datetime` in silver.
- **Negative total_amount kept** (refund/void = real revenue; payment_type 4/6). Flag `is_amount_valid`, don't filter.
- **OBT (no full star):** the 2 questions are simple aggregates, so a single denormalized `obt_trips` serves them join-free. A star (fact + dimensions) would add tables the case doesn't need.
- **`source_file` in bronze only.** It is the bronze ingestion idempotency key (append only files whose `source_file` isn't already there — the bronze table itself is the source of truth, and the atomic append means a failed run never duplicates), the source of `year`/`month` (parsed from the name), and fine-grained row→file lineage. Silver/gold derive `year`/`month` from it during conformation but don't persist it; they carry `year`/`month` + `_source_version`. Reverse lookup when needed: `_source_version` locates the bronze commit, where `source_file` lives.
- **Silver/gold idempotency:** incremental via **Delta Change Data Feed**. Each target reads only its source's new commits (`readChangeFeed` from `watermark + 1`); reruns with no new commits are no-ops. The source has CDF from creation (version 0), so the first run (`watermark = -1`) reads the feed from version 0: a single code path, no separate full-read bootstrap. The watermark is a `_source_version` column (= the source Delta version each row came from); `max(_source_version)` is the resume point, one per `taxi_type` in silver (yellow/green are separate tables), one in gold. This replaced the earlier `source_file not in (...)` anti-join, which full-scanned the source.
- **Validation, fail-fast:** silver reconciles row counts per `taxi_type` against bronze (`05_verify.py`); conformation is 1:1, so they must match. `count(*)` is metadata-only on bronze, and the silver count reads only the low-cardinality `taxi_type` column, so it is cheap, not a full scan. Gold will reconcile against silver the same way.

## Alternatives considered
Choices made against a simpler or more common option, and why:
- **Incremental: CDF vs anti-join vs managed streaming.** The first version used
  `source_file NOT IN (select … from silver)`, which full-scans the source every run. Change Data
  Feed reads only the source's new commits, so a run scales with the *delta*. Managed options (Auto
  Loader, Structured Streaming with a checkpoint, DLT) hand the watermark off to the framework, but
  Structured Streaming is limited from Databricks Connect on Free Edition, and a batch CDF read keeps
  the pipeline reproducible and explicit. In production this would move to streaming with a checkpoint,
  or DLT.
- **Ingestion idempotency: distinct + atomic append vs move vs control table.** Moving ingested files
  to a `processed` volume was tried and reverted: it is slow (server-side copy of GBs) and not
  idempotent (a partial move re-ingests and duplicates on the next run). A control table has the same
  cross-table atomicity gap (two writes can desync on a crash), and the project keeps observability in
  Delta history (no control schema). `distinct(source_file)` + an atomic append makes the bronze table
  its own source of truth; the distinct reads only one low-cardinality column, so it is cheap, not a
  full scan.
- **OBT vs star schema.** A star would add degenerate dimensions for two simple aggregate questions; a
  single denormalized `obt_trips` answers them join-free.

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
- **Bootstrap:** the source has CDF enabled from creation (version 0), so the first load reads the
  feed from version 0 (`watermark = -1`) just like any later run, then advances the watermark. One
  code path, no special-cased full read.
