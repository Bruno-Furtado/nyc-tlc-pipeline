<div align="center">

![cover](./docs/cover.webp)

[![CI](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml) ![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)

![Databricks](https://img.shields.io/badge/compute-Databricks-8B5CF6?style=flat) ![Apache Spark](https://img.shields.io/badge/compute-Apache_Spark-8B5CF6?style=flat) ![Delta Lake](https://img.shields.io/badge/data-Delta_Lake-3B82F6?style=flat) ![Unity Catalog](https://img.shields.io/badge/data-Unity_Catalog-3B82F6?style=flat) ![Delta History](https://img.shields.io/badge/observability-Delta_History-F97316?style=flat) ![Python](https://img.shields.io/badge/lang-Python-EAB308?style=flat) ![SQL](https://img.shields.io/badge/lang-SQL-EAB308?style=flat)

</div>

<div align="center">
Medallion pipeline for the NYC TLC taxi dataset on Databricks Free Edition.
</div>

## 🎬 Demo
Same pipeline, two ways to run it: **locally without a job** (just Databricks Connect, the fast dev loop), or **as an orchestrated Databricks Job** (the versioned DAG, here in prod).

**Local**: one command picks env + month range and runs every step:

```bash
python src/pipeline/run.py
```

<div align="center">
![demo](https://github.com/user-attachments/assets/f78c6380-3178-415f-9d33-5f9c5d0f9d53)
</div>

**Production**: the same pipeline triggered as the Job, on demand:

```bash
databricks bundle run nyc_tlc_pipeline --target prod
```

<div align="center">
![demo](https://github.com/user-attachments/assets/957befae-093e-4514-866e-822757cc86cd)
</div>

---

## 🗂️ Structure
```
src/pipeline/
├─ config.py            # spark, catalog, CDF helpers
├─ 00_setup.py          # catalog, schemas, volume
├─ 01_download.py       # land TLC parquet
├─ 02_bronze.py         # land → bronze (CDF on)
├─ 03_verify.py         # check bronze
├─ 04_silver.py         # bronze → silver (conform)
├─ 05_verify.py         # check silver
├─ 06_gold.py           # silver → gold (OBT)
├─ 07_verify.py         # check gold
├─ run.py               # run all, interactive
└─ reset.py             # drop the catalog
analysis/
├─ q1_total_amount.sql  # Q1: avg total_amount per month (yellow only)
└─ q2_passengers.sql    # Q2: avg passengers per hour (May 2023, all taxis)
resources/              # the Databricks Jobs (pipeline DAG + reset)
databricks.yml          # asset bundle: targets + the jobs
```

## 🌎 Environments & Dev
Free Edition is one workspace, so environments are just **separate catalogs**:
- **`nyc_tlc_dev`**: dev, the default target.
- **`nyc_tlc`**: prod. Merging to `main` deploys here.

The pipeline runs as a **Databricks Job** versioned as an **Asset Bundle**, deployed per target.

```bash
# setup (once)
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
databricks auth login --host <workspace-url>

# dev run
python src/pipeline/run.py

# dev job (deploy + run on the dev catalog)
databricks bundle deploy --target dev
databricks bundle run nyc_tlc_pipeline --target dev

# start fresh (drop the catalog)
databricks bundle run nyc_tlc_reset --target dev
```

## 🏗️ How it works
A medallion pipeline, incremental at every hop via Delta CDF. Full rationale in [docs/data-model.md](docs/data-model.md).

1. **Download**: land the TLC parquet in a volume; idempotent (`distinct(source_file)` + atomic append).
2. **Bronze**: raw, faithful to source (`source_file` added, Change Data Feed on).
3. **Silver**: conform yellow + green (canonical timestamps, typed columns, `is_amount_valid`).
4. **Gold**: `obt_trips`, a join-free OBT (consumption columns + `year`/`month`/`pickup_hour`).
5. **Analysis**: two SQL queries answer the questions (the Jan–May 2023 scope lives here).

---

<div align="center">
  <sub>Made with ♥ in Curitiba 🇧🇷 🌲 ☔️</sub>
</div>
