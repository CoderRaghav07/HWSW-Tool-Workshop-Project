import os
import logging
from datetime import datetime

from flask import Flask, request, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(level=logging.INFO)

# ============================================================
# SUPABASE CONFIG
# ============================================================
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# RISK CALCULATORS
# ============================================================
def sensor_risk_from_distance(distance):

    if distance > 150:
        return "LOW"

    elif distance > 80:
        return "MEDIUM"

    else:
        return "HIGH"


def model_risk_from_data(density, speed, weather):

    score = 0

    # Vehicle Density
    if density > 60:
        score += 3
    elif density > 30:
        score += 1

    # Speed
    if speed < 30:
        score += 2
    elif speed < 50:
        score += 1

    # Weather
    if weather >= 3:
        score += 2

    # Final Risk
    if score >= 5:
        return score, "HIGH"

    elif score >= 3:
        return score, "MEDIUM"

    else:
        return score, "LOW"


def calculate_congestion(density):

    return round(min(density / 85.0, 1.0), 6)


def calculate_accident_risk(density, speed, weather):

    base = (
        (density / 80.0) * 0.5
        + ((70 - speed) / 70.0) * 0.3
        + (weather / 5.0) * 0.2
    )

    return round(min(max(base, 0), 1), 6)

# ============================================================
# HOME ROUTE
# ============================================================
@app.route('/')
def home():

    return "Traffic Risk Server Running - Supabase Connected"

# ============================================================
# ESP32 DATA ROUTE
# ============================================================
@app.route('/data', methods=['POST'])
def receive_data():

    try:

        # ====================================================
        # GET JSON
        # ====================================================
        data = request.get_json()

        if not data:
            return jsonify({
                "error": "No JSON received"
            }), 400

        logging.info(f"Received Data: {data}")

        # ====================================================
        # EXTRACT VALUES SAFELY
        # ====================================================
        now = datetime.now()

        location = data.get("location", "UNKNOWN")

        density = float(data.get("vehicle_density") or 0)

        speed = float(data.get("avg_speed") or 0)

        weather = int(data.get("weather_code") or 1)

        distance = float(data.get("distance") or 0)

        date_only = str(now.date())

        hour = int(now.hour)

        time_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # ====================================================
        # CALCULATIONS
        # ====================================================
        sensor_risk = sensor_risk_from_distance(distance)

        risk_score, computed_risk = model_risk_from_data(
            density,
            speed,
            weather
        )

        congestion = calculate_congestion(density)

        predicted_traffic = round(
            speed * 0.9 + density * 0.3,
            4
        )

        accident_risk = calculate_accident_risk(
            density,
            speed,
            weather
        )

        # ====================================================
        # BASE ROW
        # ====================================================
        base_row = {

            "time": time_str,

            "location": location,

            "vehicle_density": density,

            "avg_speed": speed,

            "weather_code": weather,

            "distance": distance,

            "date": date_only,

            "hour": hour
        }

        # ====================================================
        # 1. LIVE TRAFFIC TABLE
        # ====================================================
        logging.info("Inserting into live_traffic")

        supabase.table("live_traffic").insert({

            **base_row,

            "risk_level": sensor_risk

        }).execute()

        logging.info("live_traffic inserted")

        # ====================================================
        # 2. OUTPUT TABLE
        # ====================================================
        logging.info("Inserting into output")

        supabase.table("output").insert({

            **base_row,

            "risk_level": computed_risk

        }).execute()

        logging.info("output inserted")

        # ====================================================
        # 3. RISK OUTPUT TABLE
        # ====================================================
        logging.info("Inserting into risk_output")

        supabase.table("risk_output").insert({

            "time": time_str,

            "location": location,

            "vehicle_count": int(density),

            "vehicle_speed": int(speed),

            "weather_code": weather,

            "distance": distance,

            "sensor_risk": sensor_risk,

            "risk_level": computed_risk,

            "date": date_only,

            "hour": hour,

            "congestion_level": congestion,

            "predicted_traffic": predicted_traffic,

            "accident_risk": accident_risk

        }).execute()

        logging.info("risk_output inserted")

        # ====================================================
        # 4. DISTRIBUTED TABLES
        # ====================================================
        risk_row = {

            **base_row,

            "risk_level": computed_risk
        }

        if computed_risk == "HIGH":

            supabase.table("high_risk").insert(
                risk_row
            ).execute()

            logging.info("high_risk inserted")

        elif computed_risk == "MEDIUM":

            supabase.table("medium_risk").insert(
                risk_row
            ).execute()

            logging.info("medium_risk inserted")

        else:

            supabase.table("low_risk").insert(
                risk_row
            ).execute()

            logging.info("low_risk inserted")

        # ====================================================
        # SUCCESS RESPONSE
        # ====================================================
        return jsonify({

            "status": "success",

            "sensor_risk": sensor_risk,

            "computed_risk": computed_risk,

            "congestion_level": congestion,

            "accident_risk": accident_risk

        }), 200

    except Exception as e:

        logging.error(f"ERROR: {str(e)}")

        return jsonify({
            "error": str(e)
        }), 500

# ============================================================
# GET ROUTES
# ============================================================
@app.route('/live', methods=['GET'])
def get_live():

    try:

        res = supabase.table(
            "live_traffic"
        ).select("*").order(
            "time",
            desc=True
        ).limit(500).execute()

        return jsonify(res.data), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route('/output', methods=['GET'])
def get_output():

    try:

        res = supabase.table(
            "output"
        ).select("*").order(
            "time",
            desc=True
        ).limit(500).execute()

        return jsonify(res.data), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route('/risk', methods=['GET'])
def get_risk():

    try:

        res = supabase.table(
            "risk_output"
        ).select("*").order(
            "time",
            desc=True
        ).limit(500).execute()

        return jsonify(res.data), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route('/high', methods=['GET'])
def get_high():

    try:

        res = supabase.table(
            "high_risk"
        ).select("*").order(
            "time",
            desc=True
        ).limit(500).execute()

        return jsonify(res.data), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route('/medium', methods=['GET'])
def get_medium():

    try:

        res = supabase.table(
            "medium_risk"
        ).select("*").order(
            "time",
            desc=True
        ).limit(500).execute()

        return jsonify(res.data), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route('/low', methods=['GET'])
def get_low():

    try:

        res = supabase.table(
            "low_risk"
        ).select("*").order(
            "time",
            desc=True
        ).limit(500).execute()

        return jsonify(res.data), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host='0.0.0.0',
        port=port
    )