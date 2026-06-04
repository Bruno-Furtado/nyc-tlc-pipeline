<div align="center">

![cover](./docs/cover.webp)

[![CI](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml) ![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json) ![License](https://img.shields.io/github/license/Bruno-Furtado/nyc-tlc-pipeline?style=flat)

![Databricks](https://img.shields.io/badge/compute-Databricks-8B5CF6?style=flat) ![Apache Spark](https://img.shields.io/badge/compute-Apache_Spark-8B5CF6?style=flat) ![Delta Lake](https://img.shields.io/badge/data-Delta_Lake-3B82F6?style=flat) ![Unity Catalog](https://img.shields.io/badge/data-Unity_Catalog-3B82F6?style=flat) ![Delta History](https://img.shields.io/badge/observability-Delta_History-F97316?style=flat) ![Python](https://img.shields.io/badge/lang-Python-EAB308?style=flat) ![SQL](https://img.shields.io/badge/lang-SQL-EAB308?style=flat)

</div>

<div align="center">
Medallion pipeline for the NYC TLC taxi dataset on Databricks Free Edition.
</div>

---

## 🗂️ Structure
```
src/
├─ pipeline/          # pipeline steps (setup now; ingest/bronze/silver/gold next)
└─ sql/00_setup.sql   # catalog, schemas and landing volume
analysis/             # the 2 answers and EDA
docs/                 # goals, plan, conventions, data model
```

## 🧑‍💻 Dev
Runs locally via Databricks Connect; targets the **dev** catalog (`nyc_tlc_dev`) by default.
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

### Lint
Config in `ruff.toml`. Run before committing:
```
ruff check src/          # report issues
ruff check --fix src/    # auto-fix what's safe (incl. import sorting)
ruff format src/         # format code
```

> No local PySpark/Java/Delta needed, `databricks-connect` ships the client.

## 🚀 Deploy
Free Edition is a single workspace, so dev/prod are isolated by **catalog**:
```
nyc_tlc_dev   # default, local/testing
nyc_tlc       # production, auto-deployed on merge to main
```

### CI
GitHub Actions (`.github/workflows/ci.yml`) runs on every PR:
```
ruff check src/
ruff format --check src/
```

> Merging a PR into `main` runs the pipeline against **prod** automatically.

## 📄 License
Released under the MIT License. See [LICENSE](LICENSE).

---

<div align="center">
  <sub>Made with ♥ in Curitiba 🌲 ☔️</sub>
</div>
