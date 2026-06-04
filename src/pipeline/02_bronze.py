"""Ingest landed TLC parquet files into bronze Delta tables.

Incremental append: each file lands once. New files (not yet in the table's
source_file set) are read, lowercased (the TLC drifts column-name case), unioned,
and appended. Spark resolves NullType and type/column differences across files via
the union; before appending we also cast the batch to the existing table's types,
so type drift across months (e.g. vendorid Integer vs Long) doesn't break the merge.
audit_id is one id per run (the load/batch), paired with ingestion_timestamp and
source_file for lineage. Schema evolution is observable via Delta history.
"""

from uuid import uuid4

from config import CATALOG, get_logger, get_spark
from databricks.sdk import WorkspaceClient
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, lit

logger = get_logger(__name__)

TAXI_TYPES = ("yellow", "green")

AUDIT_COLUMN_COMMENTS = {
    "audit_id": "Load/batch id (one per ingestion run)",
    "ingestion_timestamp": "When the row was ingested into bronze",
    "source_file": "Source parquet file name",
}


def landed_files(w: WorkspaceClient, volume_dir: str) -> set[str]:
    """Parquet names currently in the landing dir (empty before the dir exists)."""
    try:
        entries = w.files.list_directory_contents(volume_dir)
        return {e.name for e in entries if e.name.endswith(".parquet")}
    except Exception:
        return set()


def ingested_files(spark: SparkSession, table: str) -> set[str]:
    """source_file values already in the bronze table (empty if it doesn't exist)."""
    if not spark.catalog.tableExists(table):
        return set()
    rows = spark.sql(f"select distinct source_file from {table}").collect()
    return {row.source_file for row in rows}


def read_clean(spark: SparkSession, path: str, filename: str) -> DataFrame:
    """Read one parquet, lowercase column names (the TLC drifts case), tag its source file."""
    df = spark.read.parquet(path)
    df = df.toDF(*[c.lower() for c in df.columns])
    return df.withColumn("source_file", lit(filename))


def read_new_files(spark: SparkSession, volume_dir: str, filenames: list[str]) -> DataFrame:
    """Read the given landing files and union them into one DataFrame (Spark merges schemas)."""
    combined = read_clean(spark, f"{volume_dir}/{filenames[0]}", filenames[0])
    for name in filenames[1:]:
        df = read_clean(spark, f"{volume_dir}/{name}", name)
        combined = combined.unionByName(df, allowMissingColumns=True)
    return combined


def add_audit_columns(df: DataFrame, audit_id: str) -> DataFrame:
    """Stamp each row with the load's audit_id and ingestion timestamp."""
    return df.withColumn("audit_id", lit(audit_id)).withColumn(
        "ingestion_timestamp", current_timestamp()
    )


def conform_to_table(spark: SparkSession, df: DataFrame, table: str) -> DataFrame:
    """Cast columns to the table's types so an incremental append survives type drift."""
    if not spark.catalog.tableExists(table):
        return df
    for field in spark.table(table).schema:
        if field.name in df.columns:
            df = df.withColumn(field.name, df[field.name].cast(field.dataType))
    return df


def apply_metadata(spark: SparkSession, table: str, taxi: str) -> None:
    """Document the bronze table and its audit columns (idempotent)."""
    spark.sql(
        f"comment on table {table} is "
        f"'Raw {taxi} TLC trips, normalized column names plus audit columns.'"
    )
    spark.sql(f"alter table {table} set tags ('layer' = 'bronze')")
    for column, text in AUDIT_COLUMN_COMMENTS.items():
        spark.sql(f"alter table {table} alter column {column} comment '{text}'")


def count_rows(spark: SparkSession, table: str) -> int:
    """Total row count of a table."""
    return spark.sql(f"select count(*) c from {table}").collect()[0].c


def main() -> None:
    """Append every new landed file into its bronze table with audit columns."""
    spark = get_spark()
    w = WorkspaceClient()
    run_audit_id = str(uuid4())
    logger.info("bronze run audit_id=%s", run_audit_id)

    for taxi in TAXI_TYPES:
        table = f"{CATALOG}.bronze.{taxi}_tripdata_raw"
        volume_dir = f"/Volumes/{CATALOG}/bronze/landing/{taxi}"
        new_files = sorted(landed_files(w, volume_dir) - ingested_files(spark, table))
        if not new_files:
            logger.info("%s: nothing new to ingest", table)
            continue

        df = read_new_files(spark, volume_dir, new_files)
        df = add_audit_columns(df, run_audit_id)
        df = conform_to_table(spark, df, table)
        df.write.mode("append").option("mergeSchema", "true").saveAsTable(table)
        apply_metadata(spark, table, taxi)

        logger.info(
            "%s: %d new file(s), %d rows total", table, len(new_files), count_rows(spark, table)
        )


if __name__ == "__main__":
    main()
