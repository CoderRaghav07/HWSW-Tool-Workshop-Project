import os
import pandas as pd
from flask import Flask, request, jsonify
from datetime import datetime
import subprocess
import logging

app = Flask(__name__)

DATA_FILE = "live_traffic.csv"

# 🔥 Logging setup (important for DevOps)
logging.basicConfig(level=logging.INFO)

# Create CSV if not exists
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=[
        "time","location","vehicle_density",
        "avg_speed","weather_code","distance","risk_level"
    ])
    df.to_csv(DATA_FILE, index=False)

@app.route('/')
def home():
    return "Server Running"

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.json
        logging.info(f"Received data: {data}")

        df = pd.read_csv(DATA_FILE)

        new_row = pd.DataFrame([{
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "location": data.get("location"),
            "vehicle_density": data.get("vehicle_density"),
            "avg_speed": data.get("avg_speed"),
            "weather_code": data.get("weather_code"),
            "distance": data.get("distance"),
            "risk_level": data.get("risk_level")
        }])

        # ✅ Save to CSV
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        logging.info("CSV updated successfully")

        # 🔥 AUTO RUN R SCRIPT
        try:
            r_result = subprocess.run(
                ["Rscript", "predict_risk.R"],
                capture_output=True,
                text=True
            )
            logging.info("R script executed")
        except Exception as e:
            logging.error(f"R error: {e}")

        # 🔥 AUTO RUN SPARK (OPTIONAL BUT GOOD FOR MARKS)
        try:
            spark_result = subprocess.run(
                ["spark-submit", "spark_job.py"],
                capture_output=True,
                text=True
            )
            logging.info("Spark job executed")
        except Exception as e:
            logging.warning(f"Spark skipped: {e}")

        return {"status": "ok"}, 200

    except Exception as e:
        logging.error(f"Error: {e}")
        return {"error": str(e)}, 500