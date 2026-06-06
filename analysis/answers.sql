-- Answers to the two questions, read from the gold OBT (gold.obt_trips).
-- The business scope (Jan-May 2023 and the per-question rules) lives here, not in the tables.
-- Run with the gold catalog selected, e.g.  USE CATALOG nyc_tlc;  (or nyc_tlc_dev for dev).

-- Q1: average total_amount per month, yellow taxis only (Jan-May 2023).
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

-- Q2: average passengers per hour of day, May 2023, all taxis (passenger_count > 0).
select
  pickup_hour,
  round(avg(passenger_count), 2) as avg_passengers
from gold.obt_trips
where year = 2023
  and month = 5
  and passenger_count > 0
group by pickup_hour
order by pickup_hour;
