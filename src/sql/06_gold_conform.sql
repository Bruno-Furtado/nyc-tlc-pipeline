-- Conform a silver CDF batch (the `silver_changes` temp view) into gold.obt_trips.
-- Run from 06_gold.py. Silver is already unified and typed, so this just selects the consumption
-- columns, derives pickup_hour from pickup_datetime, and carries _source_version (the silver
-- version each row came from). No scope filter (that lives in analysis/answers.sql).

use catalog identifier(:catalog);

insert into gold.obt_trips
select
  vendor_id,
  passenger_count,
  total_amount,
  pickup_datetime,
  dropoff_datetime,
  taxi_type,
  year,
  month,
  hour(pickup_datetime) as pickup_hour,
  _source_version
from silver_changes;
