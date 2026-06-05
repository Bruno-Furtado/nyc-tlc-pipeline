"""Verify every landed parquet is fully represented in its bronze table.

Reconciles row counts per source_file between the landing volume and the bronze
table. Fails fast (raises) on any mismatch so the deploy stops with a clear error.
"""

from config import bronze_table, get_logger, get_spark, landing_dir
from databricks.sdk import WorkspaceClient
from pyspark.sql import SparkSession

logger = get_logger(__name__)

TAXI_TYPES = ("yellow", "green")


def landing_counts(spark: SparkSession, w: WorkspaceClient, volume_dir: str) -> dict[str, int]:
    """Row count of each landed parquet (count reads footer metadata, not the data)."""
    counts = {}
    for entry in w.files.list_directory_contents(volume_dir):
        if entry.name.endswith(".parquet"):
            counts[entry.name] = spark.read.parquet(f"{volume_dir}/{entry.name}").count()
    return counts


def bronze_counts(spark: SparkSession, table: str) -> dict[str, int]:
    """Row count per source_file already in the bronze table."""
    rows = spark.table(table).groupBy("source_file").count().collect()
    counts = {}
    for row in rows:
        counts[row.source_file] = row["count"]
    return counts


def main() -> None:
    """Reconcile landing vs bronze row counts; raise on any mismatch."""
    spark = get_spark()
    w = WorkspaceClient()
    mismatches = []

    for taxi in TAXI_TYPES:
        table = bronze_table(taxi)
        volume_dir = landing_dir(taxi)
        landing = landing_counts(spark, w, volume_dir)
        bronze = bronze_counts(spark, table)
        for name, parquet_rows in sorted(landing.items()):
            bronze_rows = bronze.get(name, 0)
            logger.info("%s %s: parquet=%d bronze=%d", taxi, name, parquet_rows, bronze_rows)
            if parquet_rows != bronze_rows:
                mismatches.append(f"{taxi}/{name} (parquet={parquet_rows}, bronze={bronze_rows})")

    if mismatches:
        raise ValueError(f"row count mismatch in {len(mismatches)} file(s): {mismatches}")
    logger.info("verification passed: all landed files fully ingested")


if __name__ == "__main__":
    main()
