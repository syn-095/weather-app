"""
services/open_meteo_marine.py
Fetches marine/ocean forecast from Open-Meteo Marine API.
No API key required.
Note: Returns None gracefully for inland locations.
"""

import requests

BASE_URL = "https://marine-api.open-meteo.com/v1/marine"


def fetch_forecast(lat: float, lon: float, days: int = 7) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "wave_height",
            "wave_direction",
            "wave_period",
            "wind_wave_height",
            "swell_wave_height",
            "swell_wave_direction",
            "swell_wave_period",
            "sea_surface_temperature",
        ],
        "daily": [
            "wave_height_max",
            "wind_wave_height_max",
            "swell_wave_height_max",
        ],
        "forecast_days": days,
        "timezone": "auto",
    }
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def normalize(raw: dict) -> dict:
    hourly = raw.get("hourly", {})
    daily  = raw.get("daily",  {})
    times  = hourly.get("time", [])

    def safe_h(key, i):
        arr = hourly.get(key, [])
        return arr[i] if i < len(arr) and arr[i] is not None else None

    hourly_records = []
    for i, t in enumerate(times):
        hourly_records.append({
            "time": t,
            "wave_height":            safe_h("wave_height", i),
            "wave_direction":         safe_h("wave_direction", i),
            "wave_period":            safe_h("wave_period", i),
            "wind_wave_height":       safe_h("wind_wave_height", i),
            "swell_wave_height":      safe_h("swell_wave_height", i),
            "swell_wave_direction":   safe_h("swell_wave_direction", i),
            "swell_wave_period":      safe_h("swell_wave_period", i),
            "sea_surface_temperature":safe_h("sea_surface_temperature", i),
        })

    d_times = daily.get("time", [])
    daily_records = []
    for i, date_str in enumerate(d_times):
        def safe_d(key, idx=i):
            arr = daily.get(key, [])
            return arr[idx] if idx < len(arr) and arr[idx] is not None else None
        daily_records.append({
            "date":                date_str,
            "wave_height_max":     safe_d("wave_height_max"),
            "wind_wave_height_max":safe_d("wind_wave_height_max"),
            "swell_wave_height_max":safe_d("swell_wave_height_max"),
        })

    return {"hourly": hourly_records, "daily": daily_records}


def is_available(raw: dict) -> bool:
    wave = raw.get("hourly", {}).get("wave_height", [])
    return any(v is not None for v in wave)