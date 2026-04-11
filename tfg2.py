import os
import pandas as pd
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "live_traffic.csv"

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
        print("Received:", data)

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

        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)

        return {"status": "ok"}, 200

    except Exception as e:
        return {"error": str(e)}, 500