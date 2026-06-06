<div align="center">

![cover](./docs/cover.webp)

[![CI](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml) ![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)

![Databricks](https://img.shields.io/badge/compute-Databricks-8B5CF6?style=flat) ![Apache Spark](https://img.shields.io/badge/compute-Apache_Spark-8B5CF6?style=flat) ![Delta Lake](https://img.shields.io/badge/data-Delta_Lake-3B82F6?style=flat) ![Unity Catalog](https://img.shields.io/badge/data-Unity_Catalog-3B82F6?style=flat) ![Delta History](https://img.shields.io/badge/observability-Delta_History-F97316?style=flat) ![Python](https://img.shields.io/badge/lang-Python-EAB308?style=flat) ![SQL](https://img.shields.io/badge/lang-SQL-EAB308?style=flat)

</div>

<div align="center">
Medallion pipeline for the NYC TLC taxi dataset on Databricks Free Edition.
</div>

## 🎬 Demo
One command (`run.py`): pick env + month range, it runs every step.

<div align="center">

![demo](https://github.com/user-attachments/assets/f78c6380-3178-415f-9d33-5f9c5d0f9d53)

</div>

---

## 🗂️ Structure
```
src/pipeline/
├─ config.py       # spark, catalog, CDF helpers
├─ 00_setup.py     # catalog, schemas, volume
├─ 01_download.py  # land TLC parquet
├─ 02_bronze.py    # land → bronze   (CDF on)
├─ 03_verify.py    # check bronze
├─ 04_silver.py    # bronze → silver (conform)
├─ 05_verify.py    # check silver
├─ 06_gold.py      # silver → gold   (OBT)
├─ 07_verify.py    # check gold
├─ run.py          # run all, interactive
└─ reset.py        # drop the catalog
src/sql/           # DDL + conform SQL per layer
analysis/          # the two answer queries (Q1, Q2)
docs/              # brief, plan, conventions, data model
```

## 🏗️ Design decisions
Full rationale in [docs/data-model.md](docs/data-model.md).
- **Incremental via Delta CDF**: reads only new commits; scales with the delta, not the table.
- **Idempotent ingest**: `distinct(source_file)` + atomic append (no file moves, no control table).
- **OBT, not a star**: the two questions are simple aggregates.
- **Spark SQL transforms**: PySpark only for ingestion and the CDF plumbing.

## 🧑‍💻 Dev
Local via Databricks Connect (no Spark/Java/Delta installed); the **dev** catalog by default.
```bash
python3.12 -m venv .venv && source .venv/bin/activate   # databricks-connect needs 3.12
pip install -r requirements.txt -r requirements-dev.txt
databricks auth login --host <workspace-url>            # via the databricks CLI
python src/pipeline/run.py                              # run everything (interactive)
```
Lint before committing, or start fresh:
```bash
ruff check src/ && ruff format src/
python src/pipeline/reset.py        # drop the whole catalog (destructive)
```

## 🚀 Deploy
One workspace, so dev/prod are split by **catalog**: `nyc_tlc_dev` (default) and `nyc_tlc` (prod, run on merge to `main`). CI runs `ruff check` + `ruff format --check` on every PR.
```bash
NYC_TLC_CATALOG=nyc_tlc python src/pipeline/reset.py   # one-off prod reset (doesn't change your shell)
```

---

<div align="center">
  <sub>Made with ♥ in Curitiba 🌲 ☔️</sub>
</div>
