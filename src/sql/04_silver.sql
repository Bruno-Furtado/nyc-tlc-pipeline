-- Silver: conform yellow + green bronze tables into one clean, consumption-ready table.
-- Incremental by source_file: each run inserts only the rows from files not yet in silver
-- (mirrors the bronze incremental). Pure conformation, NO business/scope filter — negative
-- amounts are flagged, not dropped. The Jan-May 2023 scope and the question rules live in gold.
-- year/month come from the file NAME (deterministic, immune to stray row-level dates) and the
-- table is Liquid Clustered by (year, month) so period-filtered reads prune. Incremental stays by
-- source_file because a period (e.g. 2023-05) has both a yellow and a green file.
-- Pass the target catalog as the `catalog` parameter (see config.run_sql_file).

use catalog identifier(:catalog);

-- Declare the silver contract once (idempotent). Subsequent runs only append new files.
create table if not exists silver.taxi_trips (
  vendor_id int,
  passenger_count int,
  total_amount decimal(10, 2),
  pickup_datetime timestamp,
  dropoff_datetime timestamp,
  taxi_type string,
  is_amount_valid boolean,
  year int,
  month int,
  source_file string
)
cluster by (year, month);

-- Append only the files that aren't in silver yet (incremental by source_file).
insert into silver.taxi_trips
select
  cast(vendorid as int) as vendor_id,
  cast(passenger_count as int) as passenger_count,
  cast(total_amount as decimal(10, 2)) as total_amount,
  cast(tpep_pickup_datetime as timestamp) as pickup_datetime,
  cast(tpep_dropoff_datetime as timestamp) as dropoff_datetime,
  'yellow' as taxi_type,
  coalesce(total_amount >= 0, false) as is_amount_valid,
  cast(regexp_extract(source_file, '([0-9]{4})-([0-9]{2})', 1) as int) as year,
  cast(regexp_extract(source_file, '([0-9]{4})-([0-9]{2})', 2) as int) as month,
  source_file
from bronze.yellow_tripdata_raw
where source_file not in (select distinct source_file from silver.taxi_trips)
union all
select
  cast(vendorid as int),
  cast(passenger_count as int),
  cast(total_amount as decimal(10, 2)),
  cast(lpep_pickup_datetime as timestamp),
  cast(lpep_dropoff_datetime as timestamp),
  'green',
  coalesce(total_amount >= 0, false),
  cast(regexp_extract(source_file, '([0-9]{4})-([0-9]{2})', 1) as int),
  cast(regexp_extract(source_file, '([0-9]{4})-([0-9]{2})', 2) as int),
  source_file
from bronze.green_tripdata_raw
where source_file not in (select distinct source_file from silver.taxi_trips);

-- Documentation (metadata via Unity Catalog: surfaces in Catalog Explorer).
comment on table silver.taxi_trips
  is 'Conformed yellow and green NYC taxi trips: canonical columns, no filtering. Source for the gold OBT.';
comment on column silver.taxi_trips.vendor_id
  is 'Provider that recorded the trip (TLC VendorID)';
comment on column silver.taxi_trips.passenger_count
  is 'Number of passengers reported by the driver';
comment on column silver.taxi_trips.total_amount
  is 'Total charged to the rider, can be negative on refunds or voids';
comment on column silver.taxi_trips.pickup_datetime
  is 'Trip start, canonical of yellow tpep / green lpep pickup';
comment on column silver.taxi_trips.dropoff_datetime
  is 'Trip end, canonical of yellow tpep / green lpep dropoff';
comment on column silver.taxi_trips.taxi_type
  is 'Taxi service the trip belongs to: yellow or green';
comment on column silver.taxi_trips.is_amount_valid
  is 'True only when total_amount is a real non-negative value, false when negative or missing, flag only';
comment on column silver.taxi_trips.year
  is 'Year taken from the source file name, the clustering and period key';
comment on column silver.taxi_trips.month
  is 'Month taken from the source file name, the clustering and period key';
comment on column silver.taxi_trips.source_file
  is 'Source parquet file name, carried from bronze for lineage and incremental loading';

alter table silver.taxi_trips set tags ('layer' = 'silver');
