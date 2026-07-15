"""
Cron entrypoint — runs every morning (~08:00).

Triggers POST /qc/assign-daily-hours which writes temp_qc.assigned_hours using:
  Full Working + tenure >= 1 → 9
  Full Working + tenure < 1  → 9 * tenure
  Half Working + tenure >= 1 → 4.5
  Half Working + tenure < 1  → 4.5 * tenure
  WeekOff / Leave / Holiday  → 0

Crontab example:
  0 8 * * * cd /path/to/backend-api && python assign_daily_hours.py
"""

import os
from datetime import datetime

import requests


def run():
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")
    url = f"{base_url}/qc/assign-daily-hours"

    print(f"[{datetime.now()}] Triggering roster/tenure daily hour assignment...")

    try:
        response = requests.post(url, timeout=60)
        print("Status:", response.status_code)
        print("Response:", response.text)
    except Exception as e:
        print("Error:", str(e))


if __name__ == "__main__":
    run()
