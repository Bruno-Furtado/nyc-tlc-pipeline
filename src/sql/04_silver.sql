-- Silver: the contract for the conformed yellow + green table (DDL + metadata only).
-- The conformation runs from 04_silver.py over the bronze Change Data Feed (see
-- 04_silver_conform.sql). Pure conformation, no business/scope filter: negative amounts are
-- flagged, not dropped. Carries year/month (parsed from the file name during conformation) and
-- _source_version (the bronze Delta version each row came from, the CDF watermark). source_file
-- is not propagated past bronze. Liquid Clustered by (year, month). Change Data Feed on so gold
-- reads only the new commits. Pass the target catalog as the `catalog` parameter.

use catalog identifier(:catalog);

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
  _source_version bigint
)
cluster by (year, month)
tblproperties (delta.enableChangeDataFeed = true);

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
comment on column silver.taxi_trips._source_version
  is 'Bronze Delta version each row came from, the CDF watermark for incremental loads';

alter table silver.taxi_trips set tags ('layer' = 'silver');
