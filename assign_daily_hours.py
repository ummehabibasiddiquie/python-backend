"""
Cron entrypoint — runs every morning (~08:00 IST).

Triggers /qc/assign-daily-hours which:
  - writes temp_qc.assigned_hours using:
  Full Working + tenure >= 1 → 9
  Full Working + tenure < 1  → 9 * tenure
  Half Working + tenure >= 1 → 4.5
  Half Working + tenure < 1  → 4.5 * tenure
  WeekOff / Leave / Holiday  → 0
  - writes temp_qc.qc_score = 100 for yesterday from 3 Sep 2026 onward
    (lookback 14 days) when production was 0, no file was uploaded, and
    the day was not only Training/Sample (projects 7/8).
    Days before 3 Sep with no file use Add/Edit QC on Billable.

Local / VM crontab:
  0 8 * * * cd /path/to/backend-api && API_BASE_URL=https://YOUR_API python assign_daily_hours.py

Vercel:
  Do NOT run this .py file on Vercel.
  Use vercel.json crons → GET /qc/assign-daily-hours at 08:00 IST (30 2 * * * UTC).
  Set env CRON_SECRET in Vercel; Vercel sends Authorization: Bearer <CRON_SECRET>.
"""

import os
from datetime import datetime

import requests


def run():
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    url = f"{base_url}/qc/assign-daily-hours"
    headers = {}
    cron_secret = (os.getenv("CRON_SECRET") or "").strip()
    if cron_secret:
        headers["Authorization"] = f"Bearer {cron_secret}"

    print(f"[{datetime.now()}] Triggering roster/tenure daily hour assignment → {url}")

    try:
        # Prefer GET so it matches Vercel Cron; POST also accepted by the API
        response = requests.get(url, headers=headers, timeout=60)
        print("Status:", response.status_code)
        print("Response:", response.text)
    except Exception as e:
        print("Error:", str(e))


if __name__ == "__main__":
    run()
