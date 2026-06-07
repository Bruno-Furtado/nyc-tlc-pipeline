# Analysis

Ad hoc SQL over the medallion tables, plus a narrated exploration notebook. These run on
demand (Databricks SQL editor or the notebook), they are not steps of the pipeline Job. Each
query opens with `use catalog nyc_tlc`, swap it for `nyc_tlc_dev` to hit the dev catalog.

- **exploration/**: profiling.
  - `overview.sql`: row counts per layer, dev vs prod, source files, month coverage, date range.
  - `distributions.sql`: trips by taxi type, vendor, passenger count and fare buckets.
- **quality/**: data quality.
  - `checks.sql`: nulls, negative amounts (`is_amount_valid`), bad intervals, bronze to silver to gold reconciliation.
- **questions/**: the business answers, all from gold (`obt_trips`), where the Jan to May 2023 scope lives.
  - `q1_total_amount.sql`: average total_amount per month, yellow only.
  - `q2_passengers.sql`: average passengers per hour, May 2023, all taxis.
  - `q3_revenue_by_type.sql`: revenue and average ticket per taxi type and month.
  - `q4_peak_hours.sql`: trip volume by hour of day, the demand peak.
- **notebooks/exploration.ipynb**: the same exploration narrated end to end via Databricks Connect, with charts (pandas + matplotlib).
