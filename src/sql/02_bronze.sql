-- Bronze metadata. The tables are created by 02_bronze.py (schema inferred from the source
-- parquet, raw is schema-on-read), so this file only documents them and runs after the load.
-- Pass the target catalog as the `catalog` parameter (see config.run_sql_file).

use catalog identifier(:catalog);

-- yellow

comment on table bronze.yellow_tripdata_raw
  is 'Raw yellow TLC trips, normalized column names plus a source_file column.';

alter table bronze.yellow_tripdata_raw set tags ('layer' = 'bronze');

comment on column bronze.yellow_tripdata_raw.source_file
  is 'Source parquet file name, the lineage and incremental key';

-- green

comment on table bronze.green_tripdata_raw
  is 'Raw green TLC trips, normalized column names plus a source_file column.';

alter table bronze.green_tripdata_raw set tags ('layer' = 'bronze');

comment on column bronze.green_tripdata_raw.source_file
  is 'Source parquet file name, the lineage and incremental key';
