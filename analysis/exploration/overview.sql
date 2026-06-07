-- Overview: row counts across the medallion layers, dev vs prod, the source files in bronze,
-- and the month coverage. Run statements one at a time in the SQL editor.
-- Swap nyc_tlc for nyc_tlc_dev to inspect the dev catalog.
use catalog nyc_tlc;  -- nyc_tlc_dev when running against dev

-- rows per bronze table
select 'yellow' as taxi_type, count(*) as rows from bronze.yellow_tripdata_raw
union all
select 'green', count(*) from bronze.green_tripdata_raw;

-- rows per layer for one taxi type (bronze, silver and gold must match: conformation is 1:1)
select 'bronze' as layer, count(*) as rows from bronze.yellow_tripdata_raw
union all
select 'silver', count(*) from silver.taxi_trips where taxi_type = 'yellow'
union all
select 'gold', count(*) from gold.obt_trips where taxi_type = 'yellow';

-- distinct source files and rows per taxi type in bronze (the ingestion idempotency key)
select 'yellow' as taxi_type, count(distinct source_file) as files, count(*) as rows
from bronze.yellow_tripdata_raw
union all
select 'green', count(distinct source_file), count(*)
from bronze.green_tripdata_raw;

-- dev vs prod side by side (fully qualified names, ignores the use catalog above)
select 'dev' as env, count(*) as rows, count(distinct source_file) as files
from nyc_tlc_dev.bronze.yellow_tripdata_raw
union all
select 'prod', count(*), count(distinct source_file)
from nyc_tlc.bronze.yellow_tripdata_raw;

-- months present per taxi type (year and month are parsed from the source file name)
select taxi_type, year, month, count(*) as rows
from gold.obt_trips
group by taxi_type, year, month
order by taxi_type, year, month;

-- pickup date range per taxi type (surfaces stray dates outside the published months)
select taxi_type, min(pickup_datetime) as first_pickup, max(pickup_datetime) as last_pickup
from gold.obt_trips
group by taxi_type;
