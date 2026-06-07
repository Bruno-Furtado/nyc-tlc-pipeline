# nyc-tlc-pipeline

Personal project to learn Databricks: a medallion pipeline (bronze/silver/gold) over the public NYC TLC taxi dataset, on Free Edition (serverless, Unity Catalog, Delta Lake).

## Docs
- docs/brief.md: goals & scope
- docs/conventions.md: git convention
- docs/data-model.md: modeling decisions + the 2 queries

## Language
- **All repo content is written in English**: commits, PR titles/bodies, code, comments, docs, issues. (Chat with the user stays in Portuguese.)
- **Never use a dash as a sentence separator** in prose (README, docs, comments, PR/commit text): use `:`, a comma, or split into two sentences. It reads as an AI tell. Hyphens inside identifiers and en-dash ranges (e.g. `Jan–May`) are fine.

## Git rules
- Conventional Commits: `<type>(<scope>): <desc>` (lowercase, imperative, no period). scopes: setup config ingest bronze silver gold analysis jobs
- One PR per phase, squash merge. Run `ruff` before committing.
- **Never commit directly to `main`**: always work on a branch and open a PR. Enforced by the pre-commit hook.
- Before opening a PR, review that all files are current with the change, especially the Markdown (README, CLAUDE.md, docs/).
- Every PR gets an assignee (`Bruno-Furtado`), labels (one `area:*` + one `type:*`), and the current phase milestone.

## Decisions

### Environment
- The same code runs locally (Databricks Connect) and inside a Databricks Job. `get_spark()` is dual-mode: inside the job the session already exists, so it adds `serverless(True)` only when not in the runtime (`DATABRICKS_RUNTIME_VERSION` absent → local Databricks Connect; needs `databricks-connect==18.1.*`).
- Dev/prod isolated by catalog (Free Edition is one workspace). Run knobs (`catalog`, plus `start`/`end` for the download range) resolve `--flag` (the job passes it) → env var (local `run.py`, e.g. `NYC_TLC_CATALOG`) → default, via the `config._knob` helper.

### Orchestration
- The pipeline is a **Databricks Job** (a linear DAG of 8 serverless `spark_python_task`s, one per `NN_*.py`), defined as code in a **Databricks Asset Bundle** (`databricks.yml` + `resources/pipeline.job.yml`), deployed per target with `databricks bundle deploy --target {dev,prod}`. Execution is on-demand (`bundle run` / Workflows UI); CI runs `bundle deploy --target prod` on merge (no auto-run). This replaced the temporary GitHub Actions shell-loop deploy bridge; `run.py` stays the local dev loop.
- A second job `nyc_tlc_reset` (`resources/reset.job.yml`) runs `reset.py` to drop the catalog (cascade) for a clean re-test, in both targets. `mode: production` requires an explicit `workspace.root_path`, set from `${workspace.current_user.userName}`.

### Scope
- Yellow + green only; ingest incrementally from 2023-01 to the latest published month (unpublished months return 403/404 and are skipped). Q1 = yellow only; Q2 = yellow+green, May 2023.
- Business scope (Jan–May 2023) + question rules live in the `analysis/` queries (one `.sql` per question), **not in the tables**.

### Layers & modeling
- **Transform layers in Spark SQL** (`src/sql/NN_*.sql`, run by thin Python runners via `config.run_sql_file`); PySpark stays in ingestion. No dbt. SQL files numbered like their runners.
- **Bronze** = raw, faithful to source.
- **Silver** = pure conformation, **no filter** (all months/rows): canonical timestamps (`tpep_*`/`lpep_*` → `pickup_datetime`/`dropoff_datetime`), typed columns, negative `total_amount` kept and flagged `is_amount_valid` (don't filter). Liquid Clustered by `(year, month)`.
- **Gold** = `obt_trips`, a join-free OBT (no full star): consumption columns (VendorID, passenger_count, total_amount, pickup_datetime, dropoff_datetime, taxi_type) + derived `year`/`month`/`pickup_hour`, Liquid Clustered by `(year, month)`, **no scope filter**. Answers come from here.

### Incremental, lineage & observability
- **`source_file` lives in bronze only.** It's the ingestion idempotency key (`02_bronze.py` appends only files whose `source_file` isn't already in bronze; the bronze table itself is the source of truth, and the atomic append means a failed run never duplicates) and the source of `year`/`month` (parsed from the file name, deterministic). Silver/gold derive `year`/`month` from it during conformation but **don't persist it**: they carry `year`/`month` + `_source_version` instead. Fine-grained row→file lineage is bronze-only by design.
- **Incremental via Delta Change Data Feed (CDF), not anti-join.** Bronze has `delta.enableChangeDataFeed = true` from creation (version 0). Silver/gold read only their source's new commits (`readChangeFeed`, `startingVersion = watermark + 1`); the first run (`watermark = -1`) reads the feed from version 0, so it's a single code path with no separate full-read bootstrap. The watermark is a `_source_version bigint` column (= the source Delta version each row came from); `max(_source_version)` is the resume point, one per `taxi_type` in silver (yellow/green are separate tables), one in gold. Shared helpers in `config.py` (`table_version`, `read_inserts_since`, `last_version`). This replaced the old `source_file not in (...)` incremental, which full-scanned the source.
- **Validation, fail-fast:** silver reconciles row counts per `taxi_type` against bronze (`05_verify.py`); conformation is 1:1, so they must match. `count(*)` is metadata-only on bronze; the silver count reads only the low-cardinality `taxi_type` column (not a full scan). Gold will reconcile against silver the same way.
- **Observability** via Delta history (no `control` schema), which records every load. Per-row lineage: `source_file` (bronze), `_source_version` (silver/gold).
- **Alerting** via Databricks Job `email_notifications` (declared in the bundle): both jobs email `${var.alert_email}` on failure, on success, and when a run exceeds 20 min (a `health` rule on `RUN_DURATION_SECONDS` drives `on_duration_warning_threshold_exceeded`).

### Metadata (Unity Catalog)
- `COMMENT ON … IS …` + `ALTER … SET TAGS (…)` on every UC object (both idempotent; reapply to existing objects). Descriptive, business-oriented; feeds Catalog Explorer + AI/BI Genie. `SET TAGS` rejects `IDENTIFIER(… || …)`, so `USE CATALOG` + relative schema names. `config.run_sql_file` splits each file on `;`, so keep `;` out of comments and out of `COMMENT`/`SET TAGS` text (a stray `;` in either splits a statement and breaks parsing).

### Code
- Logging (not print), fail-fast errors with clear messages, type hints required (ruff E/F/I/ANN).
