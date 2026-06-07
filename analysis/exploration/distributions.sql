-- Distributions: how trips spread across taxi type, vendor, passenger count and fare buckets.
-- This is the profiling that motivates the question filters (passenger_count > 0, negatives kept).
use catalog nyc_tlc;  -- nyc_tlc_dev when running against dev

-- share of trips per taxi type
select taxi_type, count(*) as rows,
  round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
from gold.obt_trips
group by taxi_type
order by rows desc;

-- trips per vendor
select vendor_id, count(*) as rows
from gold.obt_trips
group by vendor_id
order by rows desc;

-- passenger_count distribution (0 and nulls show up here, Q2 filters them out)
select passenger_count, count(*) as rows
from gold.obt_trips
group by passenger_count
order by passenger_count;

-- total_amount buckets (negatives are the refunds and voids we keep on purpose)
select
  case
    when total_amount < 0 then 'negative'
    when total_amount = 0 then 'zero'
    when total_amount < 20 then '0-20'
    when total_amount < 50 then '20-50'
    when total_amount < 100 then '50-100'
    else '100+'
  end as bucket,
  count(*) as rows
from gold.obt_trips
group by bucket
order by min(total_amount);
