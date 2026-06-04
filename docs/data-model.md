# Data model

## Medallion
- **bronze** — `yellow_tripdata_raw`, `green_tripdata_raw`: faithful to source + audit_id, ingestion_timestamp, source_file.
- **silver** — `taxi_trips`: yellow+green unified, canonical timestamps, typed, `is_amount_valid` flag. No business filter.
- **gold** — star schema (`fact_trips` + `dim_date`, `dim_vendor`, `dim_taxi_type`) and `obt_trips` (serving). Answers use the OBT.

Observability via Delta history (`DESCRIBE HISTORY`). Row lineage via `audit_id`.

## Decisions
- **Yellow + green only** (NYC taxis; FHV/HVFHV aren't taxis, no passenger_count). Q1 = yellow; Q2 = yellow+green.
- **Canonical timestamps:** yellow `tpep_*`, green `lpep_*` → `pickup_datetime`/`dropoff_datetime` in silver.
- **Negative total_amount kept** (refund/void = real revenue; payment_type 4/6). Flag `is_amount_valid`, don't filter.
- **Star + OBT:** star = dimensional truth; OBT = join-free serving, faster on Delta.
- **Idempotency:** overwrite by year/month partition or MERGE by key.

## Queries
```sql
-- Q1: avg total_amount per month, yellow only
select year, month, round(avg(total_amount), 2) as avg_total_amount
from nyc_tlc.gold.obt_trips
where taxi_type = 'yellow'
group by year, month
order by year, month;

-- Q2: avg passengers per hour, May 2023, all taxis
select pickup_hour, round(avg(passenger_count), 2) as avg_passengers
from nyc_tlc.gold.obt_trips
where year = 2023 and month = 5 and passenger_count > 0
group by pickup_hour
order by pickup_hour;
```

## FAQ
- **Why medallion?** Auditing, reprocessing, engineering/analytics separation.
- **Why Delta?** ACID, idempotent MERGE, schema enforcement, time travel.
- **Star and OBT?** Star is the truth; OBT serves BI without joins.
- **Negative amounts?** Refund/void is real revenue; filtering biases the average.
- **Lineage?** `audit_id` on rows + Delta history.
