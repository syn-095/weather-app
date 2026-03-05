"""
services/open_meteo_climate.py
Uses the Historical Weather API (ERA5) to compute monthly normals.
Much faster than the Climate API — returns in ~2 seconds.
Uses last 10 years of data for meaningful averages.
"""

import requests
from datetime import datetime

# Historical weather API — fast ERA5 reanalysis data
BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_climate_normals(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2015-01-01",
        "end_date": "2024-12-31",
        "daily": [
            "temperature_2m_mean",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "wind_speed_10m_mean",
        ],
        "timezone": "auto",
    }
    resp = requests.get(BASE_URL, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def normalize(raw: dict) -> dict:
    daily = raw.get("daily", {})
    times = daily.get("time", [])

    def safe(key, i):
        arr = daily.get(key, [])
        return arr[i] if i < len(arr) and arr[i] is not None else None

    # Group all days by month number across all years
    by_month = {}
    for i, date_str in enumerate(times):
        month = int(date_str[5:7])
        by_month.setdefault(month, []).append({
            "temp_mean": safe("temperature_2m_mean", i),
            "temp_max":  safe("temperature_2m_max",  i),
            "temp_min":  safe("temperature_2m_min",  i),
            "precip":    safe("precipitation_sum",    i),
            "wind":      safe("wind_speed_10m_mean",  i),
        })

    def avg(lst, key):
        vals = [x[key] for x in lst if x.get(key) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]

    monthly = []
    for month_num in sorted(by_month.keys()):
        days = by_month[month_num]
        monthly.append({
            "month":            month_num,
            "month_name":       month_names[month_num - 1],
            "temp_mean_c":      avg(days, "temp_mean"),
            "temp_max_c":       avg(days, "temp_max"),
            "temp_min_c":       avg(days, "temp_min"),
            "precipitation_mm": avg(days, "precip"),
            "wind_speed_kmh":   avg(days, "wind"),
        })

    return {"monthly_normals": monthly}