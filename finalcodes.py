"""
WOKWI CODE 

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>

const char* ssid = "Wokwi-GUEST";
const char* password = "";

// 🔥 YOUR LIVE RENDER URL
const char* serverName = "https://hwsw-tool-workshop-project.onrender.com/data";

#define TRIG_PIN 5
#define ECHO_PIN 18
#define GREEN_LED 23
#define YELLOW_LED 22
#define RED_LED 21

long duration;
float distance;

String locationID = "A12";
int weatherCode = 1;

// ================= SENSOR =================
float getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  duration = pulseIn(ECHO_PIN, HIGH, 30000);
  return duration * 0.034 / 2;
}

// ================= SETUP =================
void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected to WiFi!");
}

// ================= LOOP =================
void loop() {

  distance = random(20, 300);   // 🔥 AUTO simulation
  
  int vehicleDensity = map(distance, 300, 20, 5, 80);
  int avgSpeed = map(distance, 20, 300, 20, 70);

  String riskLevel;

  if (distance > 150) {
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(YELLOW_LED, LOW);
    digitalWrite(RED_LED, LOW);
    riskLevel = "LOW";
  } 
  else if (distance > 80) {
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(YELLOW_LED, HIGH);
    digitalWrite(RED_LED, LOW);
    riskLevel = "MEDIUM";
  } 
  else {
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(YELLOW_LED, LOW);
    digitalWrite(RED_LED, HIGH);
    riskLevel = "HIGH";
  }

  // ================= JSON =================
  String jsonData = "{";
  jsonData += "\"location\":\"" + locationID + "\",";
  jsonData += "\"vehicle_density\":" + String(vehicleDensity) + ",";
  jsonData += "\"avg_speed\":" + String(avgSpeed) + ",";
  jsonData += "\"weather_code\":" + String(weatherCode) + ",";
  jsonData += "\"distance\":" + String(distance) + ",";
  jsonData += "\"risk_level\":\"" + riskLevel + "\"}";
  
  Serial.println("Sending Data:");
  Serial.println(jsonData);

  // ================= HTTPS REQUEST =================
  if (WiFi.status() == WL_CONNECTED) {

    WiFiClientSecure client;
    client.setInsecure();   // 🔥 IMPORTANT for HTTPS

    HTTPClient https;

    https.begin(client, serverName);
    https.addHeader("Content-Type", "application/json");

    int httpResponseCode = https.POST(jsonData);

    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);

    if (httpResponseCode > 0) {
      String response = https.getString();
      Serial.println("Server response:");
      Serial.println(response);
    } else {
      Serial.println("Error sending request");
    }

    https.end();
  }

  Serial.println("-----------------------------");
  delay(5000);
}


"""


"""

TFG 2

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












"""