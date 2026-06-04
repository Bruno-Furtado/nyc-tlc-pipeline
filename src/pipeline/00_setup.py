"""Provision the catalog, schemas and landing volume for the target environment.

Runs src/sql/00_setup.sql against the catalog from NYC_TLC_CATALOG (default dev).
"""

from pathlib import Path

from config import CATALOG, get_logger, get_spark

logger = get_logger(__name__)

SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "00_setup.sql"


def statements(sql_text: str) -> list[str]:
    """Split a SQL script into individual, non-empty statements."""
    parts = sql_text.split(";")
    return [part.strip() for part in parts if part.strip()]


def main() -> None:
    """Run each statement in 00_setup.sql against the target catalog."""
    if not SQL_FILE.exists():
        raise FileNotFoundError(f"SQL file not found: {SQL_FILE}")

    spark = get_spark()
    logger.info("running setup against catalog '%s'", CATALOG)
    for statement in statements(SQL_FILE.read_text()):
        spark.sql(statement, args={"catalog": CATALOG})
    logger.info("setup done for catalog '%s'", CATALOG)


if __name__ == "__main__":
    main()
