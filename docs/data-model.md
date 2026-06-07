# Data model

How the medallion layers are shaped, how they load, and why. The pipeline is orchestrated
as a Databricks Job (a linear DAG on Databricks Workflows) defined as code in a Databricks
Asset Bundle.

## Layers

| Layer  | Table(s)                                  | Role                                                                 | Clustering        |
| ------ | ----------------------------------------- | -------------------------------------------------------------------- | ----------------- |
| Bronze | `yellow_tripdata_raw`, `green_tripdata_raw` | Raw, faithful to source + a `source_file` column. Change Data Feed on. | append (raw)      |
| Silver | `taxi_trips`                              | Yellow and green unified, conformed: canonical timestamps, typed columns, `is_amount_valid` flag. Pure conformation, no filter. | `(year, month)`   |
| Gold   | `obt_trips`                               | One join-free consumption table: consumption columns + derived year, month and pickup hour. No scope filter. Source of the answers. | `(year, month)`   |

A few things that aren't obvious from the table:

- **Silver keeps every month and row:** conformation only, no filtering. Negative amounts
  stay (see decisions below).
- **Gold has no business scope.** The Jan–May 2023 scope and the per-question rules live in
  the `analysis/` queries, not in the tables.
- **year and month come from the file name**, parsed during conformation: deterministic,
  immune to stray dates inside a row.

## Incremental loading

Both silver and gold load incrementally with **Delta Change Data Feed**: each one reads only
its source's new commits, never the whole source. This is the single mechanism behind
idempotency and scale, so it's worth stating once.

- Each layer reads its source with `readChangeFeed` starting at `watermark + 1`. The
  watermark is a `_source_version` column (the source Delta version each row came from);
  `max(_source_version)` is the resume point: one per `taxi_type` in silver (yellow and
  green are separate tables), one in gold.
- The source has Change Data Feed enabled from creation (version 0). So the **first run**
  (`watermark = -1`) reads the feed from version 0 just like any later run: one code path,
  no special-cased full read.
- A rerun with no new commits is a no-op.

Bronze ingestion is idempotent too, but differently: it appends only files whose
`source_file` isn't already in bronze (`distinct(source_file)` + an atomic append). The
bronze table is its own source of truth, so a failed run never duplicates.

## Lineage & observability

- **Per-row lineage:** `source_file` in bronze (fine-grained row → file); `_source_version`
  on silver and gold (the source commit each row came from).
- **`source_file` lives in bronze only.** Silver and gold derive year and month from it
  during conformation but don't persist it. To trace a silver/gold row back to its file,
  `_source_version` points at the bronze commit, where `source_file` lives.
- **Observability** is Delta history (`DESCRIBE HISTORY`), which already records each load's
  commit. No separate control schema.

## Metadata (comments & tags)

Every Unity Catalog object carries metadata, set as each layer is built. It surfaces in
Catalog Explorer and feeds AI/BI Genie, so it's descriptive and business-oriented.

- **Comments** use `COMMENT ON … IS …` (not inline `CREATE … COMMENT`): idempotent,
  reapplies to existing objects, while `CREATE IF NOT EXISTS` would skip them.
- **Tags** use `ALTER … SET TAGS (…)` (idempotent): `project` on the catalog, `layer` on the
  schemas, later column-level classification (e.g. PII).

Two gotchas: `SET TAGS` rejects `IDENTIFIER(:catalog || '.<schema>')`, so we `USE CATALOG`
first and tag schemas by relative name. And `run_sql_file` splits each file on `;`, so a
stray `;` inside a comment or tag text breaks parsing, so keep it out.

## Key decisions

- **Yellow and green only.** They're the NYC taxis; FHV/HVFHV aren't, and have no
  passenger_count. Q1 is yellow only; Q2 is yellow and green.
- **Ingestion scope vs business scope.** Download lands 2023-01 to the latest published
  month for both taxis (overridable per run via `NYC_TLC_START`/`NYC_TLC_END`); the TLC
  publishes whole closed months ~2 months late, and unpublished months return 403/404 and
  are skipped. The Jan–May 2023 consumption scope is applied in `analysis/`, not at
  ingestion and not in the tables.
- **Canonical timestamps.** Yellow `tpep_*` and green `lpep_*` become `pickup_datetime` /
  `dropoff_datetime` in silver.
- **Negative total_amount is kept.** Refund/void is real revenue (payment_type 4/6);
  filtering would bias the average. Flagged `is_amount_valid` instead.
- **OBT, not a star.** The two questions are simple aggregates, so one denormalized
  `obt_trips` answers them join-free. A star would add dimensions the case doesn't need.

## Validation

Silver reconciles row counts per `taxi_type` against bronze (`05_verify.py`); conformation
is 1:1, so they must match, and it fails fast otherwise. The bronze `count(*)` is
metadata-only and the silver count reads only the low-cardinality `taxi_type` column, so the
check is cheap, not a full scan. Gold reconciles against silver the same way.

## Alternatives considered

Choices made against a simpler or more common option, and why.

- **Incremental: Change Data Feed vs anti-join vs managed streaming.** The first version used
  `source_file NOT IN (select … from silver)`, which full-scans the source every run. Change
  Data Feed reads only the new commits, so a run scales with the *delta*. Managed options
  (Auto Loader, Structured Streaming with a checkpoint, DLT) hand the watermark to the
  framework, but Structured Streaming is limited from Databricks Connect on Free Edition, and
  a batch CDF read keeps the pipeline reproducible and explicit. In production this would move
  to streaming with a checkpoint, or DLT.
- **Ingestion idempotency: distinct + atomic append vs move vs control table.** Moving
  ingested files to a `processed` volume was tried and reverted: it's slow (server-side copy
  of GBs) and not idempotent (a partial move re-ingests on the next run). A control table has
  the same cross-table atomicity gap. So bronze is its own source of truth, and the distinct
  reads only one low-cardinality column.
- **OBT vs star schema.** A star would add degenerate dimensions for two simple aggregates; a
  single denormalized `obt_trips` answers them join-free.

## The questions

All answers come from gold (`obt_trips`), with the Jan to May 2023 scope applied in the query,
not in the table. The two core ones:

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

The full set lives in [`analysis/`](../analysis/README.md): `exploration/` (profiling),
`quality/` (data quality checks), `questions/` (q1 to q4, adding revenue per taxi type and the
hourly demand peak), and a narrated EDA notebook.

## FAQ

- **Why medallion?** Auditing, reprocessing, and a clean engineering/analytics split.
- **Why Delta?** ACID, idempotent MERGE, schema enforcement, time travel.
- **Why an OBT and not a star?** Two simple aggregates; one denormalized table serves them
  join-free.
- **Why keep negative amounts?** Refund/void is real revenue; filtering biases the average.
- **How does scale hold up?** Incremental reads touch only the source's new commits (Change
  Data Feed), so a run scales with the *delta*, not the table size. Physical layout lives on
  the query surfaces (silver/gold), Liquid Clustered by `(year, month)` for period-filtered
  reads; bronze stays raw append.
