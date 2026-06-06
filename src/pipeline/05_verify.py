"""Verify silver is a faithful 1:1 conformation of bronze.

Reconciles total row counts per taxi_type between the bronze raw tables and silver.taxi_trips.
Conformation keeps every row, so the counts must match. Fails fast (raises) on any mismatch.
"""

from config import CATALOG, bronze_table, get_logger, get_spark
from pyspark.sql import SparkSession

logger = get_logger(__name__)

TAXI_TYPES = ("yellow", "green")


def bronze_count(spark: SparkSession, taxi: str) -> int:
    """Total rows in a bronze raw table (count(*) is metadata-only in Delta)."""
    return spark.sql(f"select count(*) c from {bronze_table(taxi)}").first().c


def silver_counts(spark: SparkSession) -> dict[str, int]:
    """Row count per taxi_type in silver.taxi_trips."""
    rows = spark.sql(
        f"select taxi_type, count(*) c from {CATALOG}.silver.taxi_trips group by taxi_type"
    ).collect()
    return {row.taxi_type: row.c for row in rows}


def main() -> None:
    """Reconcile bronze vs silver row counts per taxi_type; raise on any mismatch."""
    spark = get_spark()
    silver = silver_counts(spark)
    mismatches = []

    for taxi in TAXI_TYPES:
        bronze = bronze_count(spark, taxi)
        silver_rows = silver.get(taxi, 0)
        logger.info("%s: bronze=%d silver=%d", taxi, bronze, silver_rows)
        if bronze != silver_rows:
            mismatches.append(f"{taxi} (bronze={bronze}, silver={silver_rows})")

    if mismatches:
        raise ValueError(f"row count mismatch in {len(mismatches)} taxi type(s): {mismatches}")
    logger.info("verification passed: silver matches bronze per taxi_type")


if __name__ == "__main__":
    main()
