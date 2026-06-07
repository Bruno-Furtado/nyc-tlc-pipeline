-- Q4: trip volume by hour of day, all taxis (May 2023): when is demand highest?
-- The business scope (month) lives here, not in the tables.
use catalog nyc_tlc;  -- nyc_tlc_dev when running against dev

select
  pickup_hour,
  count(*) as trips,
  round(100.0 * count(*) / sum(count(*)) over (), 1) as pct_of_day
from gold.obt_trips
where year = 2023
  and month = 5
group by pickup_hour
order by pickup_hour;
