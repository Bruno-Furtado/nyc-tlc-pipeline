-- Conform one taxi's bronze CDF batch (the `bronze_changes` temp view) into silver.taxi_trips.
-- Run from 04_silver.py with parameters: pickup_col / dropoff_col (the taxi's timestamp columns)
-- and taxi_type ('yellow' | 'green'). year/month come from the source file name (deterministic).
-- Negative total_amount is flagged via is_amount_valid, not filtered.

use catalog identifier(:catalog);

insert into silver.taxi_trips
select
  cast(vendorid as int) as vendor_id,
  cast(passenger_count as int) as passenger_count,
  cast(total_amount as decimal(10, 2)) as total_amount,
  cast(identifier(:pickup_col) as timestamp) as pickup_datetime,
  cast(identifier(:dropoff_col) as timestamp) as dropoff_datetime,
  :taxi_type as taxi_type,
  coalesce(total_amount >= 0, false) as is_amount_valid,
  cast(regexp_extract(source_file, '([0-9]{4})-([0-9]{2})', 1) as int) as year,
  cast(regexp_extract(source_file, '([0-9]{4})-([0-9]{2})', 2) as int) as month,
  _source_version
from bronze_changes;
