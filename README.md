# nyc-tlc-pipeline

<div align="center">

![cover](./docs/cover.webp)

[![CI](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml) ![License](https://img.shields.io/github/license/Bruno-Furtado/nyc-tlc-pipeline?style=flat) ![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)

![Databricks](https://img.shields.io/badge/compute-Databricks-8B5CF6?style=flat) ![Apache Spark](https://img.shields.io/badge/compute-Apache_Spark-8B5CF6?style=flat) ![Delta Lake](https://img.shields.io/badge/data-Delta_Lake-3B82F6?style=flat) ![Unity Catalog](https://img.shields.io/badge/data-Unity_Catalog-3B82F6?style=flat) ![Delta History](https://img.shields.io/badge/observability-Delta_History-F97316?style=flat) ![Python](https://img.shields.io/badge/lang-Python-EAB308?style=flat) ![SQL](https://img.shields.io/badge/lang-SQL-EAB308?style=flat)

</div>

<br/>

Medallion pipeline (bronze/silver/gold) for the NYC TLC taxi dataset on Databricks Free Edition (serverless, Unity Catalog, Delta Lake). PySpark for ingestion/transformation, SQL for consumption.

## Structure
```
src/
├─ pipeline/          # pipeline steps (setup now; ingest/bronze/silver/gold next)
└─ sql/00_setup.sql   # catalog, schemas and landing volume
analysis/             # the 2 answers and EDA
docs/                 # goals, plan, conventions, data model
```

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

# 4. provision the dev catalog (schemas + landing volume, with comments + tags)
python src/pipeline/00_setup.py
```

## Environments
Free Edition is a single workspace, so dev/prod are isolated by **catalog**, not by workspace:
- `nyc_tlc_dev` — default, local/testing
- `nyc_tlc` — production

### Deploy to prod
Merging a PR into `main` runs the pipeline against the **prod** catalog (`nyc_tlc`) automatically.

> The `deploy` job in `.github/workflows/ci.yml` executes every pipeline in order via Databricks Connect.

## Notes
- No local PySpark/Java/Delta needed, `databricks-connect` ships the client.
- Credentials live in `~/.databrickscfg`

## Lint
Config in `ruff.toml`. Run before committing:
```
ruff check src/          # report issues
ruff check --fix src/    # auto-fix what's safe (incl. import sorting)
ruff format src/         # format code
```

### CI
GitHub Actions (`.github/workflows/ci.yml`) runs `ruff check` + `ruff format --check` on every PR.

## License
Released under the MIT License. See [LICENSE](LICENSE).

---

<div align="center">
  <sub>Made with ♥ in Curitiba 🌲 ☔️</sub>
</div>
