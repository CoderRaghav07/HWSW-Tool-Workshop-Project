import os
from flask import Flask, request, jsonify
from datetime import datetime
import logging
from supabase import create_client, Client

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================
# SUPABASE CONNECTION
# ============================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://nhlgbwbpwzdwdefwaurb.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5obGdid2Jwd3pkd2RlZndhdXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU5ODg4NzgsImV4cCI6MjA5MTU2NDg3OH0.FzqLky6xrsPtzmjJ0VFoFoljoY2C1AjRrixtkAG3iN8")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================
# RISK CALCULATORS
# ============================================================
def sensor_risk_from_distance(distance):
    """Matches Wokwi Arduino LED logic exactly"""
    if distance > 150:   return "LOW"
    elif distance > 80:  return "MEDIUM"
    else:                return "HIGH"


def model_risk_from_data(density, speed, weather):
    """Python model risk — density + speed + weather score"""
    score = 0
    if density > 60:   score += 3
    elif density > 30: score += 1
    if speed < 30:     score += 2
    elif speed < 50:   score += 1
    if weather >= 3:   score += 2
    if score >= 5:     return score, "HIGH"
    elif score >= 3:   return score, "MEDIUM"
    else:              return score, "LOW"


def calculate_congestion(density):
    return round(min(density / 85.0, 1.0), 6)


def calculate_accident_risk(density, speed, weather):
    base = (density / 80.0) * 0.5 + ((70 - speed) / 70.0) * 0.3 + (weather / 5.0) * 0.2
    return round(min(max(base, 0), 1), 6)


# ============================================================
# ROUTES
# ============================================================
@app.route('/')
def home():
    return "Traffic Risk Server Running - Supabase Connected"


@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.json
        if not data:
            return {"error": "No JSON received"}, 400

        logging.info(f"Received: {data}")

        now       = datetime.now()
        location  = data.get("location", "UNKNOWN")
        density   = float(data.get("vehicle_density", 0))
        speed     = float(data.get("avg_speed", 0))
        weather   = int(data.get("weather_code", 1))
        distance  = float(data.get("distance", 0))
        date_only = str(now.date())
        hour      = float(now.hour)
        time_str  = now.strftime("%Y-%m-%d %H:%M:%S")

        sensor_risk               = sensor_risk_from_distance(distance)
        risk_score, computed_risk = model_risk_from_data(density, speed, weather)
        congestion                = calculate_congestion(density)
        predicted_traffic         = round(speed * 0.9 + density * 0.3, 4)
        accident_risk             = calculate_accident_risk(density, speed, weather)

        # Base row for live_traffic, output, high/medium/low tables
        base_row = {
            "time":             time_str,
            "location":         location,
            "vehicle_density":  density,
            "avg_speed":        speed,
            "weather_code":     weather,
            "distance":         distance,
            "date":             date_only,
            "hour":             hour
        }

        # ── 1. live_traffic — raw sensor data ───────────────
        supabase.table("live_traffic").insert({
            **base_row,
            "risk_level": sensor_risk
        }).execute()
        logging.info("live_traffic inserted")

        # ── 2. output — enriched with model risk ────────────
        supabase.table("output").insert({
            **base_row,
            "risk_level": computed_risk
        }).execute()
        logging.info("output inserted")

        # ── 3. risk_output — dual risk + ML metrics ─────────
        supabase.table("risk_output").insert({
            "time":               time_str,
            "location":           location,
            "vehicle_count":      int(density),
            "vehicle_speed":      int(speed),
            "weather_code":       weather,
            "distance":           distance,
            "sensor_risk":        sensor_risk,
            "risk_level":         computed_risk,
            "date":               date_only,
            "hour":               int(hour),
            "congestion_level":   congestion,
            "predicted_traffic":  predicted_traffic,
            "accident_risk":      accident_risk
        }).execute()
        logging.info("risk_output inserted")

        # ── 4. Distributed risk tables (Spark-style) ────────
        risk_row = {**base_row, "risk_level": computed_risk}

        if computed_risk == "HIGH":
            supabase.table("high_risk").insert(risk_row).execute()
            logging.info("high_risk inserted")
        elif computed_risk == "MEDIUM":
            supabase.table("medium_risk").insert(risk_row).execute()
            logging.info("medium_risk inserted")
        else:
            supabase.table("low_risk").insert(risk_row).execute()
            logging.info("low_risk inserted")

        return {
            "status":            "ok",
            "sensor_risk":       sensor_risk,
            "computed_risk":     computed_risk,
            "congestion_level":  congestion,
            "accident_risk":     accident_risk
        }, 200

    except Exception as e:
        logging.error(f"Error: {e}")
        return {"error": str(e)}, 500


# ============================================================
# READ ENDPOINTS — Power BI / R / Spark / debugging
# ============================================================
@app.route('/live', methods=['GET'])
def get_live():
    try:
        res = supabase.table("live_traffic").select("*").order("time", desc=True).limit(500).execute()
        return jsonify(res.data), 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/output', methods=['GET'])
def get_output():
    try:
        res = supabase.table("output").select("*").order("time", desc=True).limit(500).execute()
        return jsonify(res.data), 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/risk', methods=['GET'])
def get_risk():
    try:
        res = supabase.table("risk_output").select("*").order("time", desc=True).limit(500).execute()
        return jsonify(res.data), 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/high', methods=['GET'])
def get_high():
    try:
        res = supabase.table("high_risk").select("*").order("time", desc=True).limit(500).execute()
        return jsonify(res.data), 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/medium', methods=['GET'])
def get_medium():
    try:
        res = supabase.table("medium_risk").select("*").order("time", desc=True).limit(500).execute()
        return jsonify(res.data), 200
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/low', methods=['GET'])
def get_low():
    try:
        res = supabase.table("low_risk").select("*").order("time", desc=True).limit(500).execute()
        return jsonify(res.data), 200
    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)