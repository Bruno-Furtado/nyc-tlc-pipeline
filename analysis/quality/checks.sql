-- Data quality checks across silver and gold. Each query states an expectation in its comment:
-- no unexpected nulls, negatives explained, counts that reconcile. Run statements one at a time.
use catalog nyc_tlc;  -- nyc_tlc_dev when running against dev

-- nulls in the key consumption columns (passenger_count nulls are expected, the rest should be 0)
select
  count(*) as rows,
  sum(case when total_amount is null then 1 else 0 end) as null_total_amount,
  sum(case when pickup_datetime is null then 1 else 0 end) as null_pickup,
  sum(case when dropoff_datetime is null then 1 else 0 end) as null_dropoff,
  sum(case when passenger_count is null then 1 else 0 end) as null_passengers
from gold.obt_trips;

-- negative amounts: kept on purpose (refunds and voids), flagged is_amount_valid in silver
select is_amount_valid, count(*) as rows,
  min(total_amount) as min_amount, max(total_amount) as max_amount
from silver.taxi_trips
group by is_amount_valid;

-- dropoff before pickup: a data quality smell we surface but do not filter
select count(*) as bad_intervals
from gold.obt_trips
where dropoff_datetime < pickup_datetime;

-- reconciliation: row counts per layer and taxi_type (conformation is 1:1, so they must match)
select 'bronze' as layer, 'yellow' as taxi_type, count(*) as rows from bronze.yellow_tripdata_raw
union all
select 'bronze', 'green', count(*) from bronze.green_tripdata_raw
union all
select 'silver', taxi_type, count(*) from silver.taxi_trips group by taxi_type
union all
select 'gold', taxi_type, count(*) from gold.obt_trips group by taxi_type
order by taxi_type, layer;
