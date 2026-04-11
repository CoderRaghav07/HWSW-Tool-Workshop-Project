import os
import pandas as pd
from flask import Flask, request, jsonify
from datetime import datetime
import subprocess
import logging

app = Flask(__name__)

# 🔥 Use /tmp for cloud safety (Render/Azure)
DATA_FILE = os.path.join("/tmp", "live_traffic.csv")

# 🔥 Logging (important for debugging + DevOps)
logging.basicConfig(level=logging.INFO)

# Create CSV if not exists
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=[
        "time", "location", "vehicle_density",
        "avg_speed", "weather_code", "distance", "risk_level"
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

        # Load CSV
        df = pd.read_csv(DATA_FILE)

        # Create new row
        new_row = pd.DataFrame([{
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "location": data.get("location"),
            "vehicle_density": data.get("vehicle_density"),
            "avg_speed": data.get("avg_speed"),
            "weather_code": data.get("weather_code"),
            "distance": data.get("distance"),
            "risk_level": data.get("risk_level")
        }])

        # Append and save
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        logging.info("CSV updated successfully")

        # ============================
        # 🔥 R SCRIPT (LOCAL ONLY)
        # ============================
        try:
            subprocess.Popen(["Rscript", "HWSWprojectrscript.R"])
            logging.info("R script triggered")
        except Exception as e:
            logging.warning(f"R skipped (cloud): {e}")

        # ============================
        # 🔥 SPARK SCRIPT (LOCAL ONLY)
        # ============================
        try:
            subprocess.Popen(["python", "aspark.py"])
            logging.info("Spark job triggered")
        except Exception as e:
            logging.warning(f"Spark skipped (cloud): {e}")

        return {"status": "ok"}, 200

    except Exception as e:
        logging.error(f"Error: {e}")
        return {"error": str(e)}, 500