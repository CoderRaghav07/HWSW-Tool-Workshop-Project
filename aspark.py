from pyspark.sql import SparkSession
import pyodbc
import pandas as pd

spark = SparkSession.builder.appName("Traffic Monitoring").getOrCreate()

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=raghav-traffic-server.database.windows.net;"
    "DATABASE=trafficdb;"
    "UID=Areebe07;"
    "PWD=HWSWProject@CACSC603;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

pdf = pd.read_sql("SELECT * FROM traffic", conn)
df = spark.createDataFrame(pdf)

df.groupBy("location").sum("vehicle_density").show()

raw_df = df.toPandas()
high_df = df.filter(df.risk_level == "HIGH").toPandas()
medium_df = df.filter(df.risk_level == "MEDIUM").toPandas()
low_df = df.filter(df.risk_level == "LOW").toPandas()

raw_df.to_csv("raw_data.csv", index=False)
high_df.to_csv("high_risk.csv", index=False)
medium_df.to_csv("medium_risk.csv", index=False)
low_df.to_csv("low_risk.csv", index=False)

print("🔥 Spark done")