"""
backfill.py — Run this ONCE locally to upload your existing CSV data to Supabase.
"""

import pandas as pd
import numpy as np
import math
from supabase import create_client

SUPABASE_URL = "https://nhlgbwbpwzdwdefwaurb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5obGdid2Jwd3pkd2RlZndhdXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU5ODg4NzgsImV4cCI6MjA5MTU2NDg3OH0.FzqLky6xrsPtzmjJ0VFoFoljoY2C1AjRrixtkAG3iN8"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def is_bad(v):
    """Returns True if value is NaN or Infinity of ANY type"""
    try:
        return math.isnan(v) or math.isinf(v)
    except (TypeError, ValueError):
        return False


def clean_value(v):
    """Convert any value to JSON-safe Python native type"""
    if v is None:
        return None
    if is_bad(v):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        if is_bad(float(v)):
            return None
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def clean_records(records):
    """Clean every value in every row"""
    return [{k: clean_value(v) for k, v in row.items()} for row in records]


def sensor_risk(distance):
    try:
        d = float(distance)
        if d > 150:  return "LOW"
        elif d > 80: return "MEDIUM"
        else:        return "HIGH"
    except:
        return "LOW"


def upload_table(table_name, df):
    records = clean_records(df.to_dict(orient="records"))
    total = len(records)
    success = 0
    for i in range(0, total, 50):
        batch = records[i:i+50]
        try:
            supabase.table(table_name).insert(batch).execute()
            success += len(batch)
            print(f"  Uploaded rows {i+1} to {min(i+50, total)}")
        except Exception as e:
            print(f"  ERROR on rows {i+1}-{min(i+50, total)}: {e}")
            # Try row by row to isolate problem
            for j, row in enumerate(batch):
                try:
                    supabase.table(table_name).insert(row).execute()
                    success += 1
                except Exception as e2:
                    print(f"    Skipping row {i+j+1}: {e2}")
    print(f"  Done — {success}/{total} rows uploaded to {table_name}")


# ── live_traffic.csv ─────────────────────────────────────
print("\nUploading live_traffic.csv...")
df1 = pd.read_csv("live_traffic.csv")
df1.columns = [c.lower() for c in df1.columns]
df1["risk_level"] = df1["distance"].apply(sensor_risk)
upload_table("live_traffic", df1)


# ── output.csv ───────────────────────────────────────────
print("\nUploading output.csv...")
df2 = pd.read_csv("output.csv")
df2.columns = [c.lower() for c in df2.columns]
upload_table("output", df2)


# ── risk_output.csv ──────────────────────────────────────
print("\nUploading risk_output.csv...")
df3 = pd.read_csv("risk_output.csv")
df3.columns = [c.lower() for c in df3.columns]
df3["sensor_risk"] = df3["distance"].apply(sensor_risk)
upload_table("risk_output", df3)


print("\nAll done! Check your tables:")
print("https://supabase.com/dashboard/project/nhlgbwbpwzdwdefwaurb/editor")