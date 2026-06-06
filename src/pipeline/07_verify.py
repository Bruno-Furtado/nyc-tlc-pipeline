"""Verify gold is a faithful 1:1 projection of silver.

Reconciles total row counts per taxi_type between silver.taxi_trips and gold.obt_trips. Gold keeps
every silver row (no scope filter), so the counts must match. Fails fast on any mismatch.
"""

from config import CATALOG, get_logger, get_spark
from pyspark.sql import SparkSession

logger = get_logger(__name__)


def counts_by_taxi(spark: SparkSession, table: str) -> dict[str, int]:
    """Row count per taxi_type in a table (reads only the low-cardinality taxi_type column)."""
    rows = spark.sql(f"select taxi_type, count(*) c from {table} group by taxi_type").collect()
    return {row.taxi_type: row.c for row in rows}


def main() -> None:
    """Reconcile silver vs gold row counts per taxi_type; raise on any mismatch."""
    spark = get_spark()
    silver = counts_by_taxi(spark, f"{CATALOG}.silver.taxi_trips")
    gold = counts_by_taxi(spark, f"{CATALOG}.gold.obt_trips")
    mismatches = []

    for taxi in sorted(silver.keys() | gold.keys()):
        s = silver.get(taxi, 0)
        g = gold.get(taxi, 0)
        logger.info("%s: silver=%d gold=%d", taxi, s, g)
        if s != g:
            mismatches.append(f"{taxi} (silver={s}, gold={g})")

    if mismatches:
        raise ValueError(f"row count mismatch in {len(mismatches)} taxi type(s): {mismatches}")
    logger.info("verification passed: gold matches silver per taxi_type")


if __name__ == "__main__":
    main()
