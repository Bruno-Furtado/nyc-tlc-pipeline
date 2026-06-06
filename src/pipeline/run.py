"""Run the NYC TLC pipeline end to end, locally via Databricks Connect.

Interactive: asks for the environment (dev/prod) and an optional month range, sets the env vars the
steps already read (NYC_TLC_CATALOG / NYC_TLC_START / NYC_TLC_END), then runs each step in order in
one process (so the Spark session is reused). For automation, run the steps directly.
"""

import os
import runpy
from pathlib import Path

STEPS = (
    "00_setup",
    "01_download",
    "02_bronze",
    "03_verify",
    "04_silver",
    "05_verify",
    "06_gold",
    "07_verify",
)
CATALOGS = {"dev": "nyc_tlc_dev", "prod": "nyc_tlc"}


def main() -> None:
    """Ask for environment + month range, then run every step in order."""
    env = input("Environment [dev/prod] (default dev): ").strip().lower() or "dev"
    if env not in CATALOGS:
        raise SystemExit(f"unknown environment {env!r}; choose dev or prod")
    catalog = CATALOGS[env]
    os.environ["NYC_TLC_CATALOG"] = catalog

    start = input("Start month YYYY-MM (default 2023-01): ").strip()
    if start:
        os.environ["NYC_TLC_START"] = start
    end = input("End month YYYY-MM (default latest published): ").strip()
    if end:
        os.environ["NYC_TLC_END"] = end

    print(f"\nRunning on '{catalog}' for {start or '2023-01'} to {end or 'latest published'}:")
    print("  " + " -> ".join(STEPS) + "\n")

    here = Path(__file__).parent
    for step in STEPS:
        runpy.run_path(str(here / f"{step}.py"), run_name="__main__")


if __name__ == "__main__":
    main()
