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
from pyspark.sql import DataFrame

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


def run_sql_file(spark: DatabricksSession, sql_name: str, **params: str) -> None:
    """Run each `;`-separated statement of src/sql/<sql_name> against the target catalog.

    Extra keyword params are passed as named SQL args alongside `catalog`; a statement that
    doesn't reference a given param simply ignores it (e.g. `use catalog` ignores the rest)."""
    sql_path = SQL_DIR / sql_name
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")
    logger = get_logger(__name__)
    logger.info("running %s against catalog '%s'", sql_name, CATALOG)
    args = {"catalog": CATALOG, **params}
    for statement in [s.strip() for s in sql_path.read_text().split(";") if s.strip()]:
        spark.sql(statement, args=args)
    logger.info("done %s", sql_name)


def last_version(spark: DatabricksSession, table: str) -> int:
    """Latest committed Delta version of a table — the ceiling for a CDF read."""
    return spark.sql(f"describe history {table} limit 1").select("version").first().version


def table_version(spark: DatabricksSession, table: str, where: str | None = None) -> int:
    """Watermark held by a target = max(_source_version); -1 when empty or missing (first run)."""
    if not spark.catalog.tableExists(table):
        return -1
    clause = f" where {where}" if where else ""
    value = spark.sql(f"select max(_source_version) v from {table}{clause}").first().v
    return value if value is not None else -1


def read_inserts_since(spark: DatabricksSession, table: str, start_version: int) -> DataFrame:
    """Read `table`'s change log for rows inserted since start_version, each tagged with
    _source_version (the version it entered in), the watermark for incremental loads."""
    return (
        # read the change log of `table` (what got inserted/updated/deleted), not its current rows
        spark.read.format("delta")
        .option("readChangeFeed", "true")
        # each bronze write is a numbered version; start the log from start_version (inclusive)
        .option("startingVersion", start_version)
        .table(table)
        # the source is append-only, so keep only inserted rows (ignore any update/delete entries)
        .where("_change_type = 'insert'")
        # each row is tagged with the version it entered in; keep that as _source_version (our
        # "already read up to here" marker). Drop the log's bookkeeping columns and the source's own
        # _source_version if it has one (silver does), so the rename below never collides.
        .drop("_change_type", "_commit_timestamp", "_source_version")
        .withColumnRenamed("_commit_version", "_source_version")
    )
