-- Q2: average passengers per hour of day, May 2023, all taxis (passenger_count > 0).
-- The business scope (month, positive passenger counts) lives here, not in the tables.
use catalog nyc_tlc;  -- nyc_tlc_dev when running against dev

select
  pickup_hour,
  round(avg(passenger_count), 2) as avg_passengers
from gold.obt_trips
where year = 2023
  and month = 5
  and passenger_count > 0
group by pickup_hour
order by pickup_hour;
