import os
import pyodbc
import subprocess
from flask import Flask, request
from datetime import datetime
from dotenv import load_dotenv

# ============================
# 🔐 LOAD ENV
# ============================
load_dotenv()

DB_SERVER = "raghav-traffic-server.database.windows.net"
DB_NAME = "trafficdb"
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

app = Flask(__name__)

# ============================
# 🔥 DB CONNECTION
# ============================
conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

# ============================
# 🔥 INSERT DATA
# ============================
def insert_into_db(data):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='traffic' AND xtype='U')
    CREATE TABLE traffic (
        time VARCHAR(50),
        location VARCHAR(10),
        vehicle_density INT,
        avg_speed INT,
        weather_code INT,
        distance FLOAT,
        risk_level VARCHAR(10)
    )
    """)
    conn.commit()

    cursor.execute("""
    INSERT INTO traffic VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data.get("location"),
        data.get("vehicle_density"),
        data.get("avg_speed"),
        data.get("weather_code"),
        data.get("distance"),
        data.get("risk_level")
    ))

    conn.commit()
    conn.close()
    print("✅ Data inserted into Azure")

# ============================
# 🔥 RUN SPARK
# ============================
def run_spark():
    try:
        subprocess.run(["python", "aspark.py"], check=True)
        print("🔥 Spark executed")
    except Exception as e:
        print("❌ Spark error:", e)

# ============================
# 🔥 RUN R
# ============================
def run_r():
    try:
        subprocess.run(["Rscript", "HWSWprojectrscript.R"], check=True)
        print("📊 R executed")
    except Exception as e:
        print("❌ R error:", e)

# ============================
# 🌐 ROUTES
# ============================
@app.route('/')
def home():
    return "🚀 FULL PIPELINE RUNNING"

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.json
        print("📥 Received:", data)

        insert_into_db(data)

        # 🔥 AUTOMATION PIPELINE
        run_spark()
        run_r()

        return {"status": "pipeline executed"}, 200

    except Exception as e:
        print("❌ ERROR:", e)
        return {"error": str(e)}, 500

# ============================
# 🚀 MAIN
# ============================
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)