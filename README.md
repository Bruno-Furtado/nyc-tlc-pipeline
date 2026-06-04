# nyc-tlc-pipeline

Medallion pipeline (bronze/silver/gold) for the NYC TLC taxi dataset on Databricks Free Edition (serverless, Unity Catalog, Delta Lake). PySpark for ingestion/transformation, SQL for consumption.

## Structure
- `src/pipeline/` — pipeline steps (setup now; ingest/bronze/silver/gold next)
- `src/sql/00_setup.sql` — catalog, schemas and landing volume
- `analysis/` — the 2 answers and EDA
- `docs/` — goals, plan, conventions, data model

## Quickstart (dev)
Runs locally via Databricks Connect; the Spark code executes on serverless. Everything below targets the **dev** catalog (`nyc_tlc_dev`) by default.
```
# 1. virtualenv — must be Python 3.12 (databricks-connect requires it)
python3.12 -m venv .venv && source .venv/bin/activate

# 2. dependencies (runtime + ruff for linting)
pip install -r requirements.txt -r requirements-dev.txt

# 3. Databricks CLI + auth
brew tap databricks/tap && brew install databricks
databricks auth login --host <workspace-url>
# add `serverless_compute_id = auto` to the DEFAULT profile in ~/.databrickscfg

# 4. provision the dev catalog (schemas + landing volume)
python src/pipeline/00_setup.py
```

## Environments
Free Edition is a single workspace, so dev/prod are isolated by **catalog**, not by workspace:
- `nyc_tlc_dev` — default, local/testing
- `nyc_tlc` — production

Every step reads the target from `NYC_TLC_CATALOG` (default `nyc_tlc_dev`, so an unconfigured run never touches prod). To run against prod manually, set it for the command:
```
NYC_TLC_CATALOG=nyc_tlc python src/pipeline/00_setup.py
```
On Databricks itself: import the repo as a Git folder and run the same scripts.

### Deploy to prod
Merging a PR into `main` runs the pipeline against the **prod** catalog (`nyc_tlc`) automatically — the `deploy` job in `.github/workflows/ci.yml` executes every `src/pipeline/NN_*.py` in order via Databricks Connect. It needs two GitHub repo secrets: `DATABRICKS_HOST` and `DATABRICKS_TOKEN` (a workspace PAT). The job can also be triggered manually from the Actions tab (`workflow_dispatch`).

## Notes
- No local PySpark/Java/Delta needed — `databricks-connect` ships the client; only Spark ops run on serverless, plain Python (`requests`, file I/O) runs on your machine.
- Credentials live in `~/.databrickscfg` (home, not the repo): per-user secrets, read automatically by the CLI and `databricks-connect`, and never committed.

## Lint
Config in `ruff.toml`. Run before committing:
```
ruff check src/          # report issues
ruff check --fix src/    # auto-fix what's safe (incl. import sorting)
ruff format src/         # format code
```

### Pre-commit hook
A versioned hook in `.githooks/pre-commit` runs `ruff check src/` and blocks the commit if it fails. Enable it once per clone:
```
git config core.hooksPath .githooks
```

### CI
GitHub Actions (`.github/workflows/ci.yml`) runs `ruff check` + `ruff format --check` on every PR — a server-side safety net for the hook.
