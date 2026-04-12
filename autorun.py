"""
autorun.py — Full Automatic Pipeline Runner
- Pings Render every 5 mins to keep it awake
- Downloads latest Supabase data and updates CSVs
- Runs R script (risk predictions)
- Runs Spark (distributed aggregations)

Usage: python autorun.py
"""

import subprocess
import time
import logging
import pandas as pd
import requests
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ============================================================
# CONFIGURATION
# ============================================================
INTERVAL_SECONDS = 300  # 5 minutes

R_SCRIPT     = r"C:\Users\Raghav Bhargava\Downloads\HWSW workshop project\HWSWprojectrscript.R"
SPARK_SCRIPT = r"C:\Users\Raghav Bhargava\Downloads\HWSW workshop project\aspark.py"

BASE_URL = "https://hwsw-tool-workshop-project.onrender.com"

run_count = 0


# ============================================================
# STEP 0 — PING RENDER (keep alive)
# ============================================================
def ping_render():
    """Keep Render awake so it never sleeps"""
    logging.info("Pinging Render to keep it awake...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=30)
        logging.info(f"  Render is awake — status {response.status_code}")
    except Exception as e:
        logging.warning(f"  Render ping failed: {e}")


# ============================================================
# STEP 1 — UPDATE CSVs FROM SUPABASE VIA RENDER API
# ============================================================
def update_csvs():
    logging.info("Updating CSVs from Supabase...")

    endpoints = {
        "live_traffic.csv": f"{BASE_URL}/live",
        "output.csv":       f"{BASE_URL}/output",
        "risk_output.csv":  f"{BASE_URL}/risk",
    }

    for filename, url in endpoints.items():
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data:
                    df = pd.DataFrame(data)
                    df.to_csv(filename, index=False)
                    logging.info(f"  {filename} updated — {len(df)} rows")
                else:
                    logging.warning(f"  {filename} — no data returned")
            else:
                logging.warning(f"  {filename} — HTTP {response.status_code}")
        except Exception as e:
            logging.warning(f"  {filename} failed: {e}")


# ============================================================
# STEP 2 — RUN R SCRIPT
# ============================================================
def run_r_script():
    logging.info("Running R script...")
    try:
        result = subprocess.run(
            ["Rscript", R_SCRIPT],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            logging.info("  R script completed successfully")
        else:
            logging.warning(f"  R script error: {result.stderr[-300:]}")
    except subprocess.TimeoutExpired:
        logging.warning("  R script timed out")
    except FileNotFoundError:
        logging.warning("  Rscript not found — is R installed?")
    except Exception as e:
        logging.warning(f"  R script failed: {e}")


# ============================================================
# STEP 3 — RUN SPARK
# ============================================================
def run_spark():
    logging.info("Running Spark job...")
    try:
        result = subprocess.run(
            ["python", SPARK_SCRIPT],
            capture_output=True, text=True, timeout=180
        )
        if result.returncode == 0:
            logging.info("  Spark job completed successfully")
        else:
            logging.warning(f"  Spark error: {result.stderr[-300:]}")
    except subprocess.TimeoutExpired:
        logging.warning("  Spark timed out")
    except FileNotFoundError:
        logging.warning("  Python not found")
    except Exception as e:
        logging.warning(f"  Spark failed: {e}")


# ============================================================
# FULL PIPELINE
# ============================================================
def run_pipeline():
    global run_count
    run_count += 1
    logging.info(f"========== Pipeline Run #{run_count} ==========")

    ping_render()    # Wake up Render so Wokwi data keeps flowing
    update_csvs()    # Download latest → update local CSVs
    run_r_script()   # R → updates risk_output in Supabase
    run_spark()      # Spark → updates high/medium/low_risk in Supabase
    update_csvs()    # Download again → CSVs include R + Spark results

    logging.info(f"Pipeline Run #{run_count} complete!")
    logging.info(f"  Supabase updated + CSVs synced!")
    logging.info(f"  Next run in {INTERVAL_SECONDS // 60} minutes...")
    print()


# ============================================================
# MAIN LOOP
# ============================================================
if __name__ == "__main__":
    print("=" * 55)
    print("   Traffic Risk Auto Pipeline")
    print(f"   Runs every {INTERVAL_SECONDS // 60} minutes automatically")
    print("   Updates: Render + Supabase + CSVs + R + Spark")
    print("   Press Ctrl+C to stop")
    print("=" * 55)
    print()

    # Run immediately on start
    run_pipeline()

    # Then repeat every INTERVAL_SECONDS
    while True:
        time.sleep(INTERVAL_SECONDS)
        run_pipeline()