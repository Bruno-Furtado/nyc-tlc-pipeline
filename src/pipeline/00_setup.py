"""Provision the catalog, schemas and landing volume for the target environment.

Runs src/sql/00_setup.sql against the catalog from NYC_TLC_CATALOG (default dev).
"""

from config import get_spark, run_sql_file


def main() -> None:
    """Run the setup SQL against the target catalog."""
    run_sql_file(get_spark(), "00_setup.sql")


if __name__ == "__main__":
    main()
