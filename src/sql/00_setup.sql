-- Provisions one environment. Pass the target catalog as the `catalog` parameter.
-- Convention: nyc_tlc_dev (local/testing), nyc_tlc (production). Run once per catalog.
--   SQL editor:          define a parameter named `catalog`
--   Databricks Connect:  spark.sql(sql_text, args={"catalog": CATALOG})
create catalog if not exists identifier(:catalog);
create schema  if not exists identifier(:catalog || '.bronze');
create schema  if not exists identifier(:catalog || '.silver');
create schema  if not exists identifier(:catalog || '.gold');
create volume  if not exists identifier(:catalog || '.bronze.landing');
