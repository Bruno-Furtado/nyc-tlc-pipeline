<div align="center">

![cover](./docs/cover.webp)

[![CI](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Bruno-Furtado/nyc-tlc-pipeline/actions/workflows/ci.yml) ![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)

![Databricks](https://img.shields.io/badge/compute-Databricks-8B5CF6?style=flat) ![Apache Spark](https://img.shields.io/badge/compute-Apache_Spark-8B5CF6?style=flat) ![Delta Lake](https://img.shields.io/badge/data-Delta_Lake-3B82F6?style=flat) ![Unity Catalog](https://img.shields.io/badge/data-Unity_Catalog-3B82F6?style=flat) ![Databricks Asset Bundles](https://img.shields.io/badge/orchestration-Asset_Bundles-22C55E?style=flat) ![Databricks Workflows](https://img.shields.io/badge/orchestration-Workflows-22C55E?style=flat) ![Delta History](https://img.shields.io/badge/observability-Delta_History-F97316?style=flat) ![Python](https://img.shields.io/badge/lang-Python-EAB308?style=flat) ![SQL](https://img.shields.io/badge/lang-SQL-EAB308?style=flat)

</div>

<div align="center">
Medallion pipeline for the NYC TLC taxi dataset on Databricks Free Edition.
</div>

## 🚀 Setup & run

### Setup

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
databricks auth login --host <workspace-url>
```

### Local

One command runs every step (Databricks Connect).

```bash
python src/pipeline/run.py
```

<div align="center">

![demo](https://github.com/user-attachments/assets/f78c6380-3178-415f-9d33-5f9c5d0f9d53)

</div>

### Production

The same pipeline as an orchestrated Databricks Job.

```bash
databricks bundle deploy --target prod
databricks bundle run nyc_tlc_pipeline --target prod
```

<div align="center">

![demo](https://github.com/user-attachments/assets/957befae-093e-4514-866e-822757cc86cd)

</div>

> **Requires** Python 3.12 and the [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html).

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
├─ exploration/         # profiling: counts, coverage, distributions
├─ quality/             # data quality: nulls, negatives, reconciliation
├─ questions/           # the four business answers (q1..q4)
└─ notebooks/           # narrated EDA via Databricks Connect (charts)
resources/              # the Databricks Jobs (pipeline DAG + reset)
databricks.yml          # asset bundle: targets + the jobs
```

## 🗄️ Environments

Free Edition is one workspace, so environments are just **separate catalogs**:
- **`nyc_tlc_dev`**: `dev` (the default target).
- **`nyc_tlc`**: `prod` (merging to main deploys here).

## 🏗️ How it works

A medallion pipeline, incremental at every hop via Delta Change Data Feed. Full rationale in [docs/data-model.md](docs/data-model.md).

1. **Download**: land the TLC parquet in a volume; idempotent (distinct source file + atomic append).
2. **Bronze**: raw, faithful to source (adds source file, Change Data Feed on).
3. **Silver**: conform yellow and green (canonical timestamps, typed columns, `is_amount_valid`).
4. **Gold**: a join-free OBT (consumption columns + year, month and pickup hour).
5. **Analysis**: SQL for profiling and data quality, the four business answers, and a narrated EDA notebook. See [analysis/](analysis/README.md).

> In production run as a Databricks Job: a linear DAG on Databricks Workflows.
>
> The job emails you on failure, on success, and when a run goes long (over 20 min).

## 🤖 Claude subagents

- A read-only [data-engineering reviewer](.claude/agents/data-engineering-reviewer.md) audits the diff before every PR.
- A [PR flow](.claude/agents/pr-flow.md) agent ships the branch following the git conventions.

---

<div align="center">
  <sub>Made with ♥ in Curitiba 🇧🇷 🌲 ☔️</sub>
</div>
