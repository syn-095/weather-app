"""
services/open_meteo_air.py
Fetches air quality data from Open-Meteo Air Quality API.
No API key required.
Docs: https://air-quality-api.open-meteo.com
"""

import requests

BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

def fetch_air_quality(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "pm2_5",
            "pm10",
            "ozone",
            "nitrogen_dioxide",
            "uv_index",
            "european_aqi",
            "alder_pollen",
            "birch_pollen",
            "grass_pollen",
        ],
        "forecast_days": 7,
        "timezone": "auto",
    }
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def normalize(raw: dict) -> dict:
    """
    Returns a dict with:
      - current: snapshot of the most recent hour
      - daily: list of daily averages keyed by date
    """
    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])

    def safe(key, i):
        arr = hourly.get(key, [])
        return arr[i] if i < len(arr) and arr[i] is not None else None

    # Build per-hour records
    records = []
    for i, t in enumerate(times):
        records.append({
            "time": t,
            "date": t[:10],
            "pm2_5": safe("pm2_5", i),
            "pm10": safe("pm10", i),
            "ozone": safe("ozone", i),
            "nitrogen_dioxide": safe("nitrogen_dioxide", i),
            "uv_index": safe("uv_index", i),
            "european_aqi": safe("european_aqi", i),
            "alder_pollen": safe("alder_pollen", i),
            "birch_pollen": safe("birch_pollen", i),
            "grass_pollen": safe("grass_pollen", i),
        })

    # Current = most recent record
    current = records[0] if records else {}

    # Daily averages
    by_date = {}
    for r in records:
        by_date.setdefault(r["date"], []).append(r)

    def avg(lst, key):
        vals = [x[key] for x in lst if x.get(key) is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    def mx(lst, key):
        vals = [x[key] for x in lst if x.get(key) is not None]
        return round(max(vals), 2) if vals else None

    daily = []
    for date_str in sorted(by_date.keys()):
        hrs = by_date[date_str]
        daily.append({
            "date": date_str,
            "pm2_5_avg": avg(hrs, "pm2_5"),
            "pm10_avg": avg(hrs, "pm10"),
            "ozone_avg": avg(hrs, "ozone"),
            "nitrogen_dioxide_avg": avg(hrs, "nitrogen_dioxide"),
            "uv_index_max": mx(hrs, "uv_index"),
            "european_aqi_avg": avg(hrs, "european_aqi"),
            "alder_pollen_avg": avg(hrs, "alder_pollen"),
            "birch_pollen_avg": avg(hrs, "birch_pollen"),
            "grass_pollen_avg": avg(hrs, "grass_pollen"),
        })

    return {"current": current, "daily": daily}


def aqi_label(aqi: float) -> str:
    """Convert European AQI number to human-readable label."""
    if aqi is None:
        return "Unknown"
    if aqi <= 20:
        return "Good"
    if aqi <= 40:
        return "Fair"
    if aqi <= 60:
        return "Moderate"
    if aqi <= 80:
        return "Poor"
    if aqi <= 100:
        return "Very Poor"
    return "Extremely Poor"