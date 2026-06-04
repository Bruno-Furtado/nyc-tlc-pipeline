-- Provisions one environment. Pass the target catalog as the `catalog` parameter.
-- Convention: nyc_tlc_dev (local/testing), nyc_tlc (production). Run once per catalog.

-- Create the catalog first, then USE it so every other statement uses relative names
create catalog if not exists identifier(:catalog);
use catalog identifier(:catalog);

-- Create objects (idempotent via IF NOT EXISTS).
create schema if not exists bronze;
create schema if not exists silver;
create schema if not exists gold;
create volume if not exists bronze.landing;

-- Document objects. COMMENT ON is idempotent and reapplies even to existing objects.
comment on catalog identifier(:catalog)
  is 'NYC TLC taxi lakehouse, medallion over yellow and green trip records.';
comment on schema bronze
  is 'Raw layer: source files ingested as-is into Delta with a source_file column for lineage.';
comment on schema silver
  is 'Cleaned layer: yellow and green unified, canonical pickup/dropoff timestamps, typed columns, is_amount_valid flag.';
comment on schema gold
  is 'Consumption layer: obt_trips, a join-free serving table that answers the analytics questions.';
comment on volume bronze.landing
  is 'Landing zone: original TLC trip files downloaded before bronze ingestion.';

-- Tag objects for discovery/governance (also surfaced in Catalog Explorer and Genie).
alter catalog identifier(:catalog) set tags ('project' = 'nyc-tlc');
alter schema bronze set tags ('layer' = 'bronze');
alter schema silver set tags ('layer' = 'silver');
alter schema gold set tags ('layer' = 'gold');
