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
- Local + Databricks run the same code via **Databricks Connect**: `get_spark()` = `DatabricksSession.builder.serverless(True).getOrCreate()` (Free Edition is serverless; needs `databricks-connect==18.1.*`).
- Observability via Delta history (no `control` schema). Per-row lineage: `source_file` (bronze) and `_source_version` (silver/gold, the CDF watermark).
- Scope: yellow + green, incremental from 2023-01 to the latest month the TLC has published. Q1 = yellow only; Q2 = yellow+green, May 2023.
- Ingestion is incremental: `01_download.py` lands only missing months (unpublished TLC months return 403/404, skipped); `02_bronze.py` appends only files whose `source_file` isn't in bronze yet. Dedup by file name, so reruns in the same month are no-ops.
- Bronze lineage: `source_file` on each row (the lineage + incremental key); loads are versioned in Delta history (no per-row audit_id/ingestion_timestamp — Delta history already records the load).
- Consumption columns: VendorID, passenger_count, total_amount, pickup_datetime, dropoff_datetime, taxi_type.
- Canonical timestamps: tpep_*/lpep_* → pickup_datetime/dropoff_datetime in silver.
- Negative total_amount: keep + flag `is_amount_valid` (don't filter).
- Transform layers in **Spark SQL** (`src/sql/NN_*.sql`, run by thin Python runners via `config.run_sql_file`); PySpark stays in ingestion. No dbt. SQL files are numbered like their runners.
- Silver = pure conformation, **no filter** (all months/rows); **Liquid Clustered by `(year, month)`** from the file name.
- **Incremental via Delta Change Data Feed (CDF), not anti-join.** Bronze has `delta.enableChangeDataFeed = true` and stays raw. Silver and gold read only their source's new commits (`readChangeFeed`, `startingVersion = watermark + 1`), bootstrapping with a full read on the first run. The watermark is a `_source_version bigint` column on each target row (= the source Delta version it came from); `max(_source_version)` is the resume point. Silver keeps one watermark per `taxi_type` (yellow/green are separate Delta tables); gold keeps one (silver is its only source). Shared helpers in `config.py` (`table_version`, `read_inserts_since`, `last_version`). This replaced the old `source_file not in (...)` incremental, which full-scanned bronze.
- Gold = `obt_trips`, a join-free OBT: consumption columns + derived `year`/`month`/`pickup_hour`, Liquid Clustered by `(year, month)`, **no scope filter**. The Jan–May 2023 scope + question rules live in `analysis/answers.sql` (the consumption layer), not in the tables — answers come from `gold.obt_trips`.
- **Validation, fail-fast** (silver + gold): per-key row-count reconciliation (bronze↔silver by `source_file`, silver↔gold by `(year, month)`) plus value asserts (e.g. non-null timestamps, `pickup_hour` in 0–23). Reusable `config.reconcile_counts` / `config.assert_no_rows`.
- Metadata on every UC object — `COMMENT ON … IS …` and `ALTER … SET TAGS (…)` (both idempotent; reapply to existing objects). Descriptive, business-oriented; feeds Catalog Explorer + AI/BI Genie. `SET TAGS` rejects `IDENTIFIER(… || …)`, so `USE CATALOG` + relative schema names. `config.run_sql_file` strips `--` line comments before splitting on `;`, but a `;` inside a string literal still splits — keep `COMMENT`/`SET TAGS` text free of `;`.
- Dev/prod isolated by catalog via `NYC_TLC_CATALOG` (default `nyc_tlc_dev`) — Free Edition is one workspace.
- Code: logging (not print), fail-fast errors with clear messages, type hints required (ruff E/F/I/ANN).
