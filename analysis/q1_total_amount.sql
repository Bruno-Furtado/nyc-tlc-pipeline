-- Q1: average total_amount per month, yellow taxis only (Jan-May 2023).
-- The business scope (months, taxi type) lives here, not in the tables.
use catalog nyc_tlc;  -- nyc_tlc_dev when running against dev

select
  year,
  month,
  round(avg(total_amount), 2) as avg_total_amount
from gold.obt_trips
where taxi_type = 'yellow'
  and year = 2023
  and month between 1 and 5
group by year, month
order by year, month;
