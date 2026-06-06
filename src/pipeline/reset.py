"""Reset the target catalog to a clean slate (for testing).

Drops the entire catalog with CASCADE: every schema, table, volume, and the files staged in those
volumes, plus the catalog's own comment/tags. Run 00_setup.py afterwards to recreate it, then
01_download.py onward.

Targets config.CATALOG (default nyc_tlc_dev). This is destructive — point the catalog at the right
place (the job param / NYC_TLC_CATALOG) before running.
"""

from config import CATALOG, get_logger, get_spark

logger = get_logger(__name__)


def main() -> None:
    """Drop the entire target catalog (schemas, tables, volumes, files)."""
    spark = get_spark()
    logger.warning("resetting: dropping catalog '%s' (cascade)", CATALOG)
    spark.sql(f"drop catalog if exists {CATALOG} cascade")
    logger.info("dropped catalog %s — run 00_setup.py to recreate it", CATALOG)


if __name__ == "__main__":
    main()
