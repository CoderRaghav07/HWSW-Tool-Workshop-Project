from pyspark.sql import SparkSession
from pyspark.sql.functions import sum as spark_sum, avg, count, col
from supabase import create_client
import pandas as pd
import numpy as np
import math

# ============================================================
# SUPABASE CREDENTIALS
# ============================================================
SUPABASE_URL = "https://nhlgbwbpwzdwdefwaurb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5obGdid2Jwd3pkd2RlZndhdXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU5ODg4NzgsImV4cCI6MjA5MTU2NDg3OH0.FzqLky6xrsPtzmjJ0VFoFoljoY2C1AjRrixtkAG3iN8"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# SPARK SESSION
# ============================================================
spark = SparkSession.builder \
    .appName("Traffic Monitoring") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")
print("Reading data from Supabase...")

# ============================================================
# READ FROM SUPABASE
# ============================================================
res = supabase.table("live_traffic").select("*").limit(1000).execute()
pdf = pd.DataFrame(res.data)

if pdf.empty:
    print("No data in live_traffic table")
    spark.stop()
    exit()

print(f"Loaded {len(pdf)} rows from Supabase")

# ============================================================
# CREATE SPARK DATAFRAME
# ============================================================
df = spark.createDataFrame(pdf)

# ============================================================
# SPARK AGGREGATIONS
# ============================================================
print("\nVehicle density by location:")
df.groupBy("location").agg(
    spark_sum("vehicle_density").alias("total_density"),
    avg("vehicle_density").alias("avg_density"),
    avg("avg_speed").alias("avg_speed"),
    count("*").alias("total_records")
).show()

print("Risk level distribution:")
df.groupBy("risk_level").count().show()

print("Hourly traffic summary:")
df.groupBy("hour").agg(
    avg("vehicle_density").alias("avg_density"),
    avg("avg_speed").alias("avg_speed"),
    count("*").alias("records")
).orderBy("hour").show()

# ============================================================
# FILTER BY RISK LEVEL
# ============================================================
raw_df    = df.toPandas()
high_df   = df.filter(col("risk_level") == "HIGH").toPandas()
medium_df = df.filter(col("risk_level") == "MEDIUM").toPandas()
low_df    = df.filter(col("risk_level") == "LOW").toPandas()

print(f"\nRisk breakdown — HIGH: {len(high_df)} | MEDIUM: {len(medium_df)} | LOW: {len(low_df)}")

# ============================================================
# SAVE LOCAL CSV BACKUPS
# ============================================================
raw_df.to_csv("raw_data.csv", index=False)
high_df.to_csv("high_risk.csv", index=False)
medium_df.to_csv("medium_risk.csv", index=False)
low_df.to_csv("low_risk.csv", index=False)
print("Local CSV backups saved")

# ============================================================
# CLEAN VALUES FOR JSON
# ============================================================
def is_bad(v):
    try:
        return math.isnan(v) or math.isinf(v)
    except (TypeError, ValueError):
        return False

def clean_value(v):
    if v is None:                     return None
    if is_bad(v):                     return None
    if isinstance(v, (np.integer,)):  return int(v)
    if isinstance(v, (np.floating,)):
        return None if is_bad(float(v)) else float(v)
    if isinstance(v, np.bool_):       return bool(v)
    return v

def clean_records(records):
    cleaned = []
    for row in records:
        r = {k: clean_value(v) for k, v in row.items()}
        r.pop("id", None)  # remove id — let Supabase auto-generate
        cleaned.append(r)
    return cleaned

def upload_to_table(table_name, dataframe):
    if dataframe.empty:
        print(f"  No rows for {table_name} — skipping")
        return
    records = clean_records(dataframe.to_dict(orient="records"))
    success = 0
    for i in range(0, len(records), 50):
        batch = records[i:i+50]
        try:
            supabase.table(table_name).insert(batch).execute()
            success += len(batch)
            print(f"  {table_name}: uploaded rows {i+1} to {min(i+50, len(records))}")
        except Exception as e:
            print(f"  {table_name} ERROR on batch {i+1}: {e}")
    print(f"  Done — {success}/{len(records)} rows → {table_name}")

# ============================================================
# WRITE TO ALL SUPABASE TABLES
# ============================================================
print("\nWriting to Supabase tables...")

upload_to_table("output",      raw_df)    # all data
upload_to_table("high_risk",   high_df)   # HIGH only
upload_to_table("medium_risk", medium_df) # MEDIUM only
upload_to_table("low_risk",    low_df)    # LOW only

spark.stop()
print("\nSpark job completed successfully!")
print("Tables updated: output, high_risk, medium_risk, low_risk")