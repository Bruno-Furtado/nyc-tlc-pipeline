<div align="center">

![cover](./docs/cover.webp)

[![CI](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml) ![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)

![Databricks](https://img.shields.io/badge/compute-Databricks-8B5CF6?style=flat) ![Apache Spark](https://img.shields.io/badge/compute-Apache_Spark-8B5CF6?style=flat) ![Delta Lake](https://img.shields.io/badge/data-Delta_Lake-3B82F6?style=flat) ![Unity Catalog](https://img.shields.io/badge/data-Unity_Catalog-3B82F6?style=flat) ![Delta History](https://img.shields.io/badge/observability-Delta_History-F97316?style=flat) ![Python](https://img.shields.io/badge/lang-Python-EAB308?style=flat) ![SQL](https://img.shields.io/badge/lang-SQL-EAB308?style=flat)

</div>

<div align="center">
Medallion pipeline for the NYC TLC taxi dataset on Databricks Free Edition.
</div>

## 🎬 Demo

**Local** — one command picks env + month range and runs every step (Databricks Connect):
```bash
python src/pipeline/run.py
```

<div align="center">

![demo](https://github.com/user-attachments/assets/f78c6380-3178-415f-9d33-5f9c5d0f9d53)

</div>

**Production** — the same pipeline as an orchestrated Databricks Job, on demand:
```bash
databricks bundle run nyc_tlc_pipeline --target prod
```

<!-- prod run video -->

---

## 🗂️ Structure
```
src/pipeline/
├─ config.py       # spark, catalog, CDF helpers
├─ 00_setup.py     # catalog, schemas, volume
├─ 01_download.py  # land TLC parquet
├─ 02_bronze.py    # land → bronze (CDF on)
├─ 03_verify.py    # check bronze
├─ 04_silver.py    # bronze → silver (conform)
├─ 05_verify.py    # check silver
├─ 06_gold.py      # silver → gold (OBT)
├─ 07_verify.py    # check gold
├─ run.py          # run all, interactive
└─ reset.py        # drop the catalog
src/sql/           # DDL + conform SQL per layer
analysis/          # the two answer queries (Q1, Q2)
resources/         # the Databricks Jobs (pipeline DAG + reset)
databricks.yml     # asset bundle: targets + the jobs
docs/              # brief, plan, conventions, data model
```

## 🏗️ Design decisions
Full rationale in [docs/data-model.md](docs/data-model.md).
- **Incremental via Delta CDF**: reads only new commits; scales with the delta, not the table.
- **Idempotent ingest**: `distinct(source_file)` + atomic append.
- **OBT, not a star**: the two questions are simple aggregates.
- **Spark SQL transforms**: PySpark only for ingestion and the CDF plumbing.

## 🌎 Environments & dev
Free Edition is one workspace, so environments are just **separate catalogs**: `nyc_tlc_dev` (dev,
default) and `nyc_tlc` (prod). The pipeline is a **Databricks Job** versioned as an **Asset Bundle**;
merging to `main` deploys prod (CI runs `bundle deploy --target prod`).

```bash
# setup (once)
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
databricks auth login --host <workspace-url>

# dev job: deploy + run on the dev catalog
databricks bundle deploy --target dev
databricks bundle run nyc_tlc_pipeline --target dev

# lint before committing
ruff check src/ && ruff format src/

# start fresh: drop the catalog
databricks bundle run nyc_tlc_reset --target dev
```

---

<div align="center">
  <sub>Made with ♥ in Curitiba 🌲 ☔️</sub>
</div>
