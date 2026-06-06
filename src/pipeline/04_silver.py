"""Build the silver layer incrementally from the bronze Change Data Feed.

For each taxi, read only bronze's new commits (readChangeFeed from the stored watermark), conform
them in Spark SQL over a temp view, and append to silver.taxi_trips. The watermark is
max(_source_version) per taxi_type; the first run (watermark -1) reads the feed from version 0.
Validation lives in 05_verify.py.
"""

from config import (
    CATALOG,
    bronze_table,
    get_logger,
    get_spark,
    last_version,
    read_inserts_since,
    run_sql_file,
    table_version,
)

logger = get_logger(__name__)

# taxi -> (pickup column, dropoff column) in bronze (column names are lowercased on ingest)
TAXIS = {
    "yellow": ("tpep_pickup_datetime", "tpep_dropoff_datetime"),
    "green": ("lpep_pickup_datetime", "lpep_dropoff_datetime"),
}


def main() -> None:
    """Conform each bronze table's new CDF commits into silver.taxi_trips."""
    spark = get_spark()
    run_sql_file(spark, "04_silver.sql")  # DDL + metadata (idempotent)
    silver = f"{CATALOG}.silver.taxi_trips"

    # yellow and green are separate bronze tables with independent histories, so each keeps its
    # own watermark; they conform into the same silver table (taxi_type tells them apart).
    for taxi, (pickup_col, dropoff_col) in TAXIS.items():
        bronze = bronze_table(taxi)
        # watermark = highest bronze version already in silver for this taxi (-1 on the first run);
        # ceiling = bronze's latest version. We want everything in between.
        watermark = table_version(spark, silver, where=f"taxi_type = '{taxi}'")
        ceiling = last_version(spark, bronze)
        if watermark >= ceiling:
            # already read up to the latest version: nothing new, and reading past it would error.
            logger.info("%s: silver up to date (watermark %d)", taxi, watermark)
            continue

        # the new rows: bronze's change log from the first unread version onward.
        changes = read_inserts_since(spark, bronze, watermark + 1)
        if changes.isEmpty():
            # versions advanced but added no rows (e.g. a metadata-only commit like SET TAGS).
            logger.info("%s: no new bronze inserts since version %d", taxi, watermark)
            continue

        # hand the batch to the conform SQL as a temp view; it casts/derives and appends to silver,
        # carrying _source_version so the next run resumes from here.
        changes.createOrReplaceTempView("bronze_changes")
        run_sql_file(
            spark,
            "04_silver_conform.sql",
            pickup_col=pickup_col,
            dropoff_col=dropoff_col,
            taxi_type=taxi,
        )
        logger.info("%s: conformed bronze CDF versions %d..%d", taxi, watermark + 1, ceiling)


if __name__ == "__main__":
    main()
