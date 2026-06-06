"""Ingest landed TLC parquet files into bronze Delta tables.

Incremental append: each file lands once. A run reads only the landing files not yet in the
table (their source_file isn't present) and appends them. This is idempotent and never
duplicates: the append is one atomic Delta commit, so a failure either lands the batch fully
or not at all, and a rerun skips whatever is already there. Files are lowercased (the TLC
drifts column-name case), unioned, and cast to the existing table's types before appending,
so type drift across months (e.g. vendorid Integer vs Long) doesn't break the merge. Each row
carries source_file for lineage; each load is versioned in Delta history. Bronze is created
with Change Data Feed enabled so silver/gold can read its new commits incrementally.

The bronze schema is inferred from the source parquet (raw = schema-on-read); table
comments and tags are declared in src/sql/02_bronze.sql, applied after the load.

Functions are ordered by the call sequence (callers before the helpers they call); main, the
entry point, sits at the bottom.
"""

from config import bronze_table, get_logger, get_spark, landing_dir, run_sql_file
from databricks.sdk import WorkspaceClient
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import lit

logger = get_logger(__name__)

TAXI_TYPES = ("yellow", "green")


def landed_files(w: WorkspaceClient, volume_dir: str) -> set[str]:
    """Parquet names currently in the landing dir (empty before the dir exists)."""
    try:
        entries = w.files.list_directory_contents(volume_dir)
        return {e.name for e in entries if e.name.endswith(".parquet")}
    except Exception:
        return set()


def ingested_files(spark: SparkSession, table: str) -> set[str]:
    """source_file values already in bronze (empty if it doesn't exist). Reads only that one
    low-cardinality column, so it's cheap — not a full data scan."""
    if not spark.catalog.tableExists(table):
        return set()
    rows = spark.sql(f"select distinct source_file from {table}").collect()
    return {row.source_file for row in rows}


def read_new_files(spark: SparkSession, volume_dir: str, filenames: list[str]) -> DataFrame:
    """Read the given landing files and union them into one DataFrame (Spark merges schemas)."""
    combined = read_clean(spark, f"{volume_dir}/{filenames[0]}", filenames[0])
    for name in filenames[1:]:
        df = read_clean(spark, f"{volume_dir}/{name}", name)
        # union by column name (not position); allowMissingColumns fills absent cols with null,
        # so months with a different column set (e.g. airport_fee) merge instead of erroring.
        combined = combined.unionByName(df, allowMissingColumns=True)
    return combined


def read_clean(spark: SparkSession, path: str, filename: str) -> DataFrame:
    """Read one parquet, lowercase column names (the TLC drifts case), tag its source file."""
    df = spark.read.parquet(path)
    df = df.toDF(*[c.lower() for c in df.columns])
    return df.withColumn("source_file", lit(filename))


def conform_to_table(spark: SparkSession, df: DataFrame, table: str) -> DataFrame:
    """Cast columns to the table's types so an incremental append survives type drift."""
    if not spark.catalog.tableExists(table):
        return df
    for field in spark.table(table).schema:
        if field.name in df.columns:
            df = df.withColumn(field.name, df[field.name].cast(field.dataType))
    return df


def written_rows(spark: SparkSession, table: str) -> int:
    """Rows written by the latest commit, read from Delta history (metadata, no data scan)."""
    history = spark.sql(f"describe history {table} limit 1").select("operationMetrics").first()
    return int(history.operationMetrics.get("numOutputRows", 0))


def main() -> None:
    """Append every new landed file into its bronze table, then document the tables."""
    spark = get_spark()
    w = WorkspaceClient()

    # yellow and green are separate tables, ingested in sequence: one saveAsTable already
    # spreads across the whole serverless cluster, so running the two at once wouldn't help.
    for taxi in TAXI_TYPES:
        table = bronze_table(taxi)
        volume_dir = landing_dir(taxi)
        # only files not already in bronze; the bronze table itself is the source of truth for
        # what's ingested, so a failed run never duplicates (the append commit is atomic).
        new_files = sorted(landed_files(w, volume_dir) - ingested_files(spark, table))
        if not new_files:
            logger.info("%s: nothing new to ingest", table)
            continue

        # read + conform are lazy (just a query plan); Spark runs it, parallelized per file
        # and row group, on the write below.
        df = read_new_files(spark, volume_dir, new_files)
        df = conform_to_table(spark, df, table)
        (
            df.write.mode("append")  # add rows, don't overwrite
            .option("mergeSchema", "true")  # let new columns extend the table
            .option("delta.enableChangeDataFeed", "true")  # turn CDF on at table creation (v0)
            .saveAsTable(table)  # action: runs the plan, registers a UC managed table
        )
        # rows written come from the commit's operationMetrics (Delta history), not a data scan.
        rows = written_rows(spark, table)
        logger.info("%s: %d new file(s), %d rows ingested", table, len(new_files), rows)

    run_sql_file(spark, "02_bronze.sql")


if __name__ == "__main__":
    main()
