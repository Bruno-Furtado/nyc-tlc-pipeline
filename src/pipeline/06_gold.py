"""Build the gold OBT incrementally from the silver Change Data Feed.

Read only silver's new commits (readChangeFeed from the stored watermark), conform them in Spark SQL
over a temp view, and append to gold.obt_trips. Silver is the only source, so there's a single
watermark = max(_source_version); the first run (watermark -1) reads the feed from version 0.
Validation lives in 07_verify.py.
"""

from config import (
    CATALOG,
    get_logger,
    get_spark,
    last_version,
    read_inserts_since,
    run_sql_file,
    table_version,
)

logger = get_logger(__name__)


def main() -> None:
    """Conform silver's new CDF commits into gold.obt_trips."""
    spark = get_spark()
    run_sql_file(spark, "06_gold.sql")  # DDL + metadata (idempotent)
    gold = f"{CATALOG}.gold.obt_trips"
    silver = f"{CATALOG}.silver.taxi_trips"

    # single source (silver), so a single watermark = highest silver version already in gold
    # (-1 on the first run); ceiling = silver's latest version. We want everything in between.
    watermark = table_version(spark, gold)
    ceiling = last_version(spark, silver)
    if watermark >= ceiling:
        # already read up to the latest version: nothing new, and reading past it would error.
        logger.info("gold up to date (watermark %d)", watermark)
        return

    changes = read_inserts_since(spark, silver, watermark + 1)
    if changes.isEmpty():
        # versions advanced but added no rows (e.g. a metadata-only commit like SET TAGS).
        logger.info("no new silver inserts since version %d", watermark)
        return

    # hand the batch to the conform SQL as a temp view; it derives pickup_hour and appends to gold,
    # carrying _source_version so the next run resumes from here.
    changes.createOrReplaceTempView("silver_changes")
    run_sql_file(spark, "06_gold_conform.sql")
    logger.info("conformed silver CDF versions %d..%d", watermark + 1, ceiling)


if __name__ == "__main__":
    main()
