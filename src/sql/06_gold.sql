-- Gold: the contract for obt_trips, a join-free One Big Table (DDL + metadata only).
-- The conformation runs from 06_gold.py over the silver Change Data Feed (see 06_gold_conform.sql).
-- Consumption columns straight from silver + derived pickup_hour, no scope filter (the Jan-May 2023
-- scope and the question rules live in analysis/answers.sql). Carries _source_version (the silver
-- Delta version each row came from). Liquid Clustered by (year, month). No Change Data Feed: gold is
-- the serving layer, nothing reads its feed. Pass the target catalog as the `catalog` parameter.

use catalog identifier(:catalog);

create table if not exists gold.obt_trips (
  vendor_id int,
  passenger_count int,
  total_amount decimal(10, 2),
  pickup_datetime timestamp,
  dropoff_datetime timestamp,
  taxi_type string,
  year int,
  month int,
  pickup_hour int,
  _source_version bigint
)
cluster by (year, month);

-- Documentation (metadata via Unity Catalog: surfaces in Catalog Explorer and feeds Genie).
comment on table gold.obt_trips
  is 'Join-free OBT of NYC taxi trips: consumption columns + derived period and hour. Source of the analytics answers.';
comment on column gold.obt_trips.vendor_id
  is 'Provider that recorded the trip (TLC VendorID)';
comment on column gold.obt_trips.passenger_count
  is 'Number of passengers reported by the driver';
comment on column gold.obt_trips.total_amount
  is 'Total charged to the rider, can be negative on refunds or voids';
comment on column gold.obt_trips.pickup_datetime
  is 'Trip start (canonical pickup from silver)';
comment on column gold.obt_trips.dropoff_datetime
  is 'Trip end (canonical dropoff from silver)';
comment on column gold.obt_trips.taxi_type
  is 'Taxi service the trip belongs to: yellow or green';
comment on column gold.obt_trips.year
  is 'Year of the trip period, the clustering and filter key';
comment on column gold.obt_trips.month
  is 'Month of the trip period, the clustering and filter key';
comment on column gold.obt_trips.pickup_hour
  is 'Hour of day (0-23) of the pickup, derived for the per-hour question';
comment on column gold.obt_trips._source_version
  is 'Silver Delta version each row came from, the CDF watermark for incremental loads';

alter table gold.obt_trips set tags ('layer' = 'gold');
