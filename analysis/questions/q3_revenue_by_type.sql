-- Q3: total revenue, trips and average ticket per taxi type and month (Jan-May 2023).
-- The business scope (months) lives here, not in the tables.
use catalog nyc_tlc;  -- nyc_tlc_dev when running against dev

select
  taxi_type,
  year,
  month,
  count(*) as trips,
  round(sum(total_amount), 2) as total_revenue,
  round(avg(total_amount), 2) as avg_ticket
from gold.obt_trips
where year = 2023
  and month between 1 and 5
group by taxi_type, year, month
order by taxi_type, year, month;
