-- Provisions one environment. Pass the target catalog as the `catalog` parameter.
-- Convention: nyc_tlc_dev (local/testing), nyc_tlc (production). Run once per catalog.
--   SQL editor:          define a parameter named `catalog`
--   Databricks Connect:  spark.sql(sql_text, args={"catalog": CATALOG})

-- Create objects (idempotent via IF NOT EXISTS).
create catalog if not exists identifier(:catalog);
create schema  if not exists identifier(:catalog || '.bronze');
create schema  if not exists identifier(:catalog || '.silver');
create schema  if not exists identifier(:catalog || '.gold');
create volume  if not exists identifier(:catalog || '.bronze.landing');

-- Document objects. COMMENT ON is idempotent and reapplies even to existing objects
-- (unlike CREATE IF NOT EXISTS). Descriptions surface in Catalog Explorer and feed
-- AI/BI Genie, so keep them descriptive and business-oriented.
comment on catalog identifier(:catalog)
  is 'NYC TLC taxi lakehouse — medallion (bronze/silver/gold) over public yellow & green trip records, Jan–May 2023.';
comment on schema identifier(:catalog || '.bronze')
  is 'Raw layer: source files ingested as-is into Delta with audit columns (audit_id, ingestion_timestamp, source_file).';
comment on schema identifier(:catalog || '.silver')
  is 'Cleaned layer: yellow & green unified, canonical pickup/dropoff timestamps, typed columns, is_amount_valid flag, no business filtering.';
comment on schema identifier(:catalog || '.gold')
  is 'Consumption layer: star schema (fact_trips + dim_date/dim_vendor/dim_taxi_type) and obt_trips for join-free BI/serving.';
comment on volume identifier(:catalog || '.bronze.landing')
  is 'Landing zone: original TLC trip files downloaded before bronze ingestion.';

-- Tag objects for discovery/governance (also surfaced in Catalog Explorer and Genie).
-- ALTER ... SET TAGS is idempotent and reapplies to existing objects. It doesn't accept
-- IDENTIFIER(:catalog || '.<schema>'), so we USE the catalog and tag schemas by relative name.
use catalog identifier(:catalog);
alter catalog identifier(:catalog) set tags ('project' = 'nyc-tlc');
alter schema bronze set tags ('layer' = 'bronze');
alter schema silver set tags ('layer' = 'silver');
alter schema gold   set tags ('layer' = 'gold');
