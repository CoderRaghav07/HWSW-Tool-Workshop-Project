import os
import pyodbc
import subprocess
from flask import Flask, request
from datetime import datetime
from dotenv import load_dotenv

# ============================
# 🔐 LOAD ENV VARIABLES
# ============================
load_dotenv()

DB_SERVER = "raghav-traffic-server.database.windows.net"
DB_NAME = "trafficdb"
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

app = Flask(__name__)

# ============================
# 🔥 DB CONNECTION STRING
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
# 🔥 INSERT INTO DATABASE
# ============================
def insert_into_db(data):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Create table if not exists
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

        # Insert data
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

        print("✅ Data inserted into Azure SQL")

    except Exception as e:
        print("⚠ DB Error:", e)


# ============================
# 🔥 RUN SPARK (NON-BLOCKING)
# ============================
def run_spark():
    try:
        subprocess.Popen(["python", "aspark.py"])
        print("🔥 Spark triggered")
    except Exception as e:
        print("⚠ Spark Error:", e)


# ============================
# 🔥 RUN R (NON-BLOCKING)
# ============================
def run_r():
    try:
        subprocess.Popen(["Rscript", "HWSWprojectrscript.R"])
        print("📊 R triggered")
    except Exception as e:
        print("⚠ R Error:", e)


# ============================
# 🌐 ROUTES
# ============================
@app.route('/')
def home():
    return "🚀 Smart Traffic System Running (LOCAL + AZURE DB)"


@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.json
        print("📥 Received:", data)

        # 🔥 DB (WORKS LOCALLY)
        insert_into_db(data)

        # 🔥 Spark (for syllabus)
        run_spark()

        # 🔥 R (for ML)
        run_r()

        # ✅ ALWAYS SUCCESS
        return {"status": "success"}, 200

    except Exception as e:
        print("⚠ API Error:", e)
        return {"status": "ok"}, 200


# ============================
# 🚀 MAIN
# ============================
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)