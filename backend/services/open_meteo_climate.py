import os
import json
import time
import requests

BASE_URL  = "https://archive-api.open-meteo.com/v1/archive"
CACHE_DIR = "/tmp/climate_cache"


def _cache_path(lat, lon):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return f"{CACHE_DIR}/{round(lat, 2)}_{round(lon, 2)}.json"


def _load_cache(lat, lon):
    path = _cache_path(lat, lon)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        if time.time() - data.get("cached_at", 0) < 604800:
            return data.get("normals")
    except Exception:
        pass
    return None


def _save_cache(lat, lon, normals):
    try:
        with open(_cache_path(lat, lon), "w") as f:
            json.dump({"cached_at": time.time(), "normals": normals}, f)
    except Exception:
        pass


def fetch_climate_normals(lat: float, lon: float) -> dict:
    cached = _load_cache(lat, lon)
    if cached:
        return {"_from_cache": True, "monthly_normals": cached, "_lat": lat, "_lon": lon}

    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": "2015-01-01",
        "end_date":   "2024-12-31",
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
    data = resp.json()
    data["_lat"] = lat
    data["_lon"] = lon
    return data


def normalize(raw: dict) -> dict:
    lat = raw.get("_lat")
    lon = raw.get("_lon")

    if raw.get("_from_cache"):
        return {"monthly_normals": raw["monthly_normals"]}

    daily = raw.get("daily", {})
    times = daily.get("time", [])

    def safe(key, i):
        arr = daily.get(key, [])
        return arr[i] if i < len(arr) and arr[i] is not None else None

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

    _save_cache(lat, lon, monthly)
    return {"monthly_normals": monthly}