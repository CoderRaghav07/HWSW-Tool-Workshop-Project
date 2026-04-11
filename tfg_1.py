import time
import requests
import json
import os
import pandas as pd
import subprocess
import threading
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "live_traffic.csv"
RISK_FILE = "risk_output.csv"

# PUT YOUR webhook.site TOKEN HERE
WEBHOOK_TOKEN = "a44c0f84-2cd4-43d1-af34-47e72488c211"

WEBHOOK_API = f"https://webhook.site/token/{WEBHOOK_TOKEN}/requests?sorting=newest"

# UPDATE if your R version differs
R_SCRIPT_PATH = r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe"

last_uuid = None

# Create CSV if not exists
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=[
        "time",
        "date",
        "hour",
        "location",
        "vehicle_density",
        "avg_speed",
        "weather_code",
        "distance",
        "risk_level"
    ])
    df.to_csv(DATA_FILE, index=False)


def fetch_webhook_data():
    global last_uuid

    while True:
        try:
            headers = {"Accept": "application/json"}
            r = requests.get(WEBHOOK_API, headers=headers)

            if r.status_code != 200:
                print("Webhook API error:", r.status_code)
                time.sleep(5)
                continue

            data = r.json()

            if data["data"]:
                latest = data["data"][0]

                if latest["uuid"] != last_uuid:
                    last_uuid = latest["uuid"]

                    payload_raw = latest["content"]
                    payload = json.loads(payload_raw)

                    print("New ESP32 Data:", payload)

                    df = pd.read_csv(DATA_FILE)

                    # Generate dynamic timestamp
                    now = datetime.now()

                    new_row = pd.DataFrame([{
                        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "date": now.strftime("%Y-%m-%d"),
                        "hour": now.hour,
                        "location": payload["location"],
                        "vehicle_density": float(payload["vehicle_density"]),
                        "avg_speed": float(payload["avg_speed"]),
                        "weather_code": int(payload["weather_code"]),
                        "distance": float(payload["distance"]),
                        "risk_level": payload["risk_level"]
                    }])

                    df = pd.concat([df, new_row], ignore_index=True)
                    df.to_csv(DATA_FILE, index=False)

                    print("CSV Updated with Dynamic Time")

                    # Run R prediction
                    result = subprocess.run(
                        [R_SCRIPT_PATH, "predict_risk.R"],
                        capture_output=True,
                        text=True
                    )

                    print("R Output:\n", result.stdout)
                    print("⚠ R Errors:\n", result.stderr)

        except Exception as e:
            print("Error fetching webhook:", e)

        time.sleep(5)


@app.route('/')
def home():
    return "Smart Traffic Accident Prediction Server Running"


@app.route('/risk-data', methods=['GET'])
def send_risk_data():
    if os.path.exists(RISK_FILE):
        df = pd.read_csv(RISK_FILE)
        return df.to_json(orient="records")
    else:
        return jsonify({"message": "No risk data yet"}), 404


if __name__ == '__main__':

    # Start webhook listener
    thread = threading.Thread(target=fetch_webhook_data)
    thread.daemon = True
    thread.start()

    app.run(host="0.0.0.0", port=5000, debug=True)