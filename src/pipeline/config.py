"""Pipeline configuration.

The target catalog is environment-driven so the same code provisions and writes
to dev or prod without changes. Free Edition is a single workspace, so we isolate
environments by Unity Catalog, not by workspace:
    nyc_tlc_dev  — default, local/testing
    nyc_tlc      — production
"""

import logging
import os
from pathlib import Path

from databricks.connect import DatabricksSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CATALOG = os.environ.get("NYC_TLC_CATALOG", "nyc_tlc_dev")
SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def get_spark() -> DatabricksSession:
    """Spark session — same call locally (Databricks Connect) and on Databricks."""
    return DatabricksSession.builder.serverless(True).getOrCreate()


def get_logger(name: str) -> logging.Logger:
    """Return a logger using the shared format configured at import time."""
    return logging.getLogger(name)


def landing_dir(taxi: str) -> str:
    """Landing volume directory for a taxi type (where downloads are staged before bronze)."""
    return f"/Volumes/{CATALOG}/bronze/landing/{taxi}"


def bronze_table(taxi: str) -> str:
    """Fully qualified name of the bronze table for a taxi type."""
    return f"{CATALOG}.bronze.{taxi}_tripdata_raw"


def run_sql_file(spark: DatabricksSession, sql_name: str) -> None:
    """Run each `;`-separated statement of src/sql/<sql_name> against the target catalog.
    """
    sql_path = SQL_DIR / sql_name
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")
    logger = get_logger(__name__)
    logger.info("running %s against catalog '%s'", sql_name, CATALOG)
    for statement in [s.strip() for s in sql_path.read_text().split(";") if s.strip()]:
        spark.sql(statement, args={"catalog": CATALOG})
    logger.info("done %s", sql_name)
