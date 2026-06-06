# nyc-tlc-pipeline

Personal project to learn Databricks: a medallion pipeline (bronze/silver/gold) over the public NYC TLC taxi dataset, on Free Edition (serverless, Unity Catalog, Delta Lake).

## Docs
- docs/brief.md — goals & scope
- docs/runbook.md — step-by-step plan + current state
- docs/conventions.md — git convention
- docs/data-model.md — modeling decisions + the 2 queries

## Language
- **All repo content is written in English**: commits, PR titles/bodies, code, comments, docs, issues. (Chat with the user stays in Portuguese.)

## Git rules
- Conventional Commits: `<type>(<scope>): <desc>` (lowercase, imperative, no period). scopes: setup config ingest bronze silver gold analysis jobs
- One PR per phase, squash merge. Run `ruff` before committing.
- **Never commit directly to `main`** — always work on a branch and open a PR. Enforced by the pre-commit hook.
- Before opening a PR, review that all files are current with the change — especially the Markdown (README, CLAUDE.md, docs/).
- Every PR gets an assignee (`Bruno-Furtado`), labels (one `area:*` + one `type:*`), and the current phase milestone.

## Decisions

### Environment
- Local + Databricks run the same code via **Databricks Connect**: `get_spark()` = `DatabricksSession.builder.serverless(True).getOrCreate()` (Free Edition is serverless; needs `databricks-connect==18.1.*`).
- Dev/prod isolated by catalog via `NYC_TLC_CATALOG` (default `nyc_tlc_dev`) — Free Edition is one workspace.

### Scope
- Yellow + green only; ingest incrementally from 2023-01 to the latest published month (unpublished months return 403/404 and are skipped). Q1 = yellow only; Q2 = yellow+green, May 2023.
- Business scope (Jan–May 2023) + question rules live in `analysis/answers.sql`, **not in the tables**.

### Layers & modeling
- **Transform layers in Spark SQL** (`src/sql/NN_*.sql`, run by thin Python runners via `config.run_sql_file`); PySpark stays in ingestion. No dbt. SQL files numbered like their runners.
- **Bronze** = raw, faithful to source.
- **Silver** = pure conformation, **no filter** (all months/rows): canonical timestamps (`tpep_*`/`lpep_*` → `pickup_datetime`/`dropoff_datetime`), typed columns, negative `total_amount` kept and flagged `is_amount_valid` (don't filter). Liquid Clustered by `(year, month)`.
- **Gold** = `obt_trips`, a join-free OBT (no full star): consumption columns (VendorID, passenger_count, total_amount, pickup_datetime, dropoff_datetime, taxi_type) + derived `year`/`month`/`pickup_hour`, Liquid Clustered by `(year, month)`, **no scope filter**. Answers come from here.

### Incremental, lineage & observability
- **`source_file` lives in bronze only.** It's the ingestion idempotency key (`02_bronze.py` appends only files whose `source_file` isn't already in bronze; the bronze table itself is the source of truth, and the atomic append means a failed run never duplicates) and the source of `year`/`month` (parsed from the file name, deterministic). Silver/gold derive `year`/`month` from it during conformation but **don't persist it** — they carry `year`/`month` + `_source_version` instead. Fine-grained row→file lineage is bronze-only by design.
- **Incremental via Delta Change Data Feed (CDF), not anti-join.** Bronze has `delta.enableChangeDataFeed = true`. Silver/gold read only their source's new commits (`readChangeFeed`, `startingVersion = watermark + 1`), bootstrapping with a full read on the first run. The watermark is a `_source_version bigint` column (= the source Delta version each row came from); `max(_source_version)` is the resume point — one per `taxi_type` in silver (yellow/green are separate tables), one in gold. Shared helpers in `config.py` (`table_version`, `read_inserts_since`, `last_version`). This replaced the old `source_file not in (...)` incremental, which full-scanned the source.
- **Validation, fail-fast** (silver + gold): row-count reconciliation per period `(year, month)` (bronze↔silver, silver↔gold) plus value asserts (e.g. non-null timestamps, `pickup_hour` in 0–23). Reusable `config.reconcile_counts` / `config.assert_no_rows`.
- **Observability** via Delta history (no `control` schema), which records every load. Per-row lineage: `source_file` (bronze), `_source_version` (silver/gold).

### Metadata (Unity Catalog)
- `COMMENT ON … IS …` + `ALTER … SET TAGS (…)` on every UC object (both idempotent; reapply to existing objects). Descriptive, business-oriented; feeds Catalog Explorer + AI/BI Genie. `SET TAGS` rejects `IDENTIFIER(… || …)`, so `USE CATALOG` + relative schema names. `config.run_sql_file` strips `--` line comments before splitting on `;`, but a `;` inside a string literal still splits — keep `COMMENT`/`SET TAGS` text free of `;`.

### Code
- Logging (not print), fail-fast errors with clear messages, type hints required (ruff E/F/I/ANN).
