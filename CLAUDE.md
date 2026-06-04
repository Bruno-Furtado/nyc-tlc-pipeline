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
- Observability via Delta history (no `control` schema).
- Scope: yellow + green, incremental from 2023-01 to the latest month the TLC has published. Q1 = yellow only; Q2 = yellow+green, May 2023.
- Ingestion is incremental: `01_download.py` lands only missing months (unpublished TLC months return 403/404, skipped); `02_bronze.py` appends only files whose `source_file` isn't in bronze yet. Dedup by file name, so reruns in the same month are no-ops.
- Bronze audit columns: `audit_id` (one per ingestion run/batch), `ingestion_timestamp`, `source_file`.
- Consumption columns: VendorID, passenger_count, total_amount, pickup_datetime, dropoff_datetime, taxi_type.
- Canonical timestamps: tpep_*/lpep_* → pickup_datetime/dropoff_datetime in silver.
- Negative total_amount: keep + flag `is_amount_valid` (don't filter).
- Answers come from `gold.obt_trips`.
- Metadata on every UC object — `COMMENT ON … IS …` and `ALTER … SET TAGS (…)` (both idempotent; reapply to existing objects). Descriptive, business-oriented; feeds Catalog Explorer + AI/BI Genie. `SET TAGS` rejects `IDENTIFIER(… || …)`, so `USE CATALOG` + relative schema names. Keep comment/tag text free of `;` (the `00_setup.py` splitter breaks on it).
- Dev/prod isolated by catalog via `NYC_TLC_CATALOG` (default `nyc_tlc_dev`) — Free Edition is one workspace.
- Code: logging (not print), fail-fast errors with clear messages, type hints required (ruff E/F/I/ANN).
