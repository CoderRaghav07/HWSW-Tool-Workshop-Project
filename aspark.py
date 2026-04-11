from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("Traffic Monitoring") \
    .getOrCreate()

df = spark.read.csv("live_traffic.csv", header=True, inferSchema=True)
df.groupBy("location").sum("vehicle_density").show()
# 🔹 RAW DATA (complete dataset)
raw_df = df.toPandas()
print("\nRAW DATA:")
print(raw_df)

# 🔹 HIGH risk
high_df = df.filter(df.risk_level == "HIGH").toPandas()
print("\nHIGH RISK DATA:")
print(high_df)

# 🔹 MEDIUM risk
medium_df = df.filter(df.risk_level == "MEDIUM").toPandas()
print("\nMEDIUM RISK DATA:")
print(medium_df)

# 🔹 LOW risk
low_df = df.filter(df.risk_level == "LOW").toPandas()
print("\nLOW RISK DATA:")
print(low_df)

# 🔹 Save all tables (VERY USEFUL)
raw_df.to_csv("raw_data.csv", index=False)
high_df.to_csv("high_risk.csv", index=False)
medium_df.to_csv("medium_risk.csv", index=False)
low_df.to_csv("low_risk.csv", index=False)