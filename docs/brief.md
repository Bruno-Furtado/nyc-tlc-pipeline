# Brief

Personal learning project: hands-on Databricks (Lakehouse, medallion, PySpark, Delta) over the public NYC TLC taxi dataset.

## Goal
Ingest NYC taxi trips into a Lakehouse, expose a clean SQL consumption layer, and answer 2 questions.

## Data
TLC trip records (https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). Scope: Jan–May 2023.

## Requirements
- Land original files in a landing zone, then model a consumption layer from scratch.
- Use PySpark for ingestion/transformation; expose via SQL.
- Surface at least: VendorID, passenger_count, total_amount, pickup_datetime, dropoff_datetime, taxi_type.

## Questions
- Q1: average `total_amount` per month, yellow taxis only.
- Q2: average `passenger_count` per hour of day in May, all taxis (yellow + green).

## Stack
Databricks Free Edition (serverless, Unity Catalog), Delta Lake, PySpark, SQL. Local dev via Databricks Connect.
