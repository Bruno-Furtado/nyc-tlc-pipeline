"""Build the silver layer by running src/sql/04_silver.sql against the target catalog.

Silver conforms the yellow and green bronze tables into one clean table (canonical columns,
no filtering). The transformation lives in readable Spark SQL; this runner just executes it.
"""

from config import get_spark, run_sql_file


def main() -> None:
    """Run the silver SQL on Spark (Databricks Connect)."""
    run_sql_file(get_spark(), "04_silver.sql")


if __name__ == "__main__":
    main()
