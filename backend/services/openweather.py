"""
services/openweather.py
Fetches weather from OpenWeatherMap (1000 calls/day free tier).
Docs: https://openweathermap.org/api/one-call-3
"""

import os
import requests
from datetime import datetime, timezone
from models.weather import HourlyPoint, DailyPoint

BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"

def _get_key():
    key = os.getenv("OPENWEATHER_API_KEY", "")
    if not key:
        raise EnvironmentError("OPENWEATHER_API_KEY not set.")
    return key

OWM_ICONS = {
    "01": "clear",
    "02": "partly-cloudy",
    "03": "cloudy",
    "04": "cloudy",
    "09": "showers",
    "10": "rain",
    "11": "thunder",
    "13": "snow",
    "50": "fog",
}

def _icon_slug(icon_code: str) -> str:
    return OWM_ICONS.get(icon_code[:2], "unknown")

def fetch_forecast(lat: float, lon: float) -> dict:
    key = _get_key()
    params = {
        "lat": lat,
        "lon": lon,
        "appid": key,
        "units": "metric",
        "exclude": "minutely,alerts",
    }
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def normalize(raw: dict):
    hourly_raw = raw.get("hourly", [])
    daily_raw  = raw.get("daily",  [])
    current_raw = raw.get("current", {})

    # Hourly
    hourly_by_date = {}
    for h in hourly_raw:
        dt = datetime.fromtimestamp(h["dt"], tz=timezone.utc)
        time_str = dt.strftime("%Y-%m-%dT%H:%M")
        date_str = time_str[:10]
        weather = h.get("weather", [{}])[0]
        icon_code = weather.get("icon", "01d")

        hp = HourlyPoint(
            time=time_str,
            temperature_c=round(float(h.get("temp", 0)), 1),
            feels_like_c=round(float(h.get("feels_like", 0)), 1),
            humidity_pct=round(float(h.get("humidity", 0)), 1),
            precipitation_mm=round(
                float(h.get("rain", {}).get("1h", 0) or
                      h.get("snow", {}).get("1h", 0)), 2
            ),
            wind_speed_kmh=round(float(h.get("wind_speed", 0)) * 3.6, 1),
            wind_direction_deg=int(h.get("wind_deg", 0)),
            weather_code=weather.get("id", 800),
            description=weather.get("description", "").capitalize(),
            icon=_icon_slug(icon_code),
            source="openweather",
        )
        hp.__dict__["precipitation_probability"] = round(
            float(h.get("pop", 0)) * 100, 1
        )
        hp.__dict__["uv_index"] = h.get("uvi")
        hourly_by_date.setdefault(date_str, []).append(hp)

    # Daily
    daily_points = []
    for d in daily_raw:
        dt = datetime.fromtimestamp(d["dt"], tz=timezone.utc)
        date_str = dt.strftime("%Y-%m-%d")
        weather = d.get("weather", [{}])[0]
        icon_code = weather.get("icon", "01d")
        hrs = hourly_by_date.get(date_str, [])

        sunrise_str = datetime.fromtimestamp(
            d.get("sunrise", 0), tz=timezone.utc
        ).strftime("%H:%M") if d.get("sunrise") else None
        sunset_str = datetime.fromtimestamp(
            d.get("sunset", 0), tz=timezone.utc
        ).strftime("%H:%M") if d.get("sunset") else None

        temp = d.get("temp", {})
        dp = DailyPoint(
            date=date_str,
            temp_max_c=round(float(temp.get("max", 0)), 1),
            temp_min_c=round(float(temp.get("min", 0)), 1),
            temp_avg_c=round(float(temp.get("day", 0)), 1),
            precipitation_mm=round(float(d.get("rain", 0) or d.get("snow", 0)), 2),
            humidity_avg_pct=round(float(d.get("humidity", 0)), 1),
            wind_max_kmh=round(float(d.get("wind_speed", 0)) * 3.6, 1),
            wind_avg_kmh=round(float(d.get("wind_speed", 0)) * 3.6, 1),
            weather_code=weather.get("id", 800),
            description=weather.get("description", "").capitalize(),
            icon=_icon_slug(icon_code),
            sunrise=sunrise_str,
            sunset=sunset_str,
            source="openweather",
            hourly=hrs,
        )
        daily_points.append(dp)

    # Current
    current = None
    if current_raw:
        dt = datetime.fromtimestamp(current_raw["dt"], tz=timezone.utc)
        weather = current_raw.get("weather", [{}])[0]
        icon_code = weather.get("icon", "01d")
        current = HourlyPoint(
            time=dt.strftime("%Y-%m-%dT%H:%M"),
            temperature_c=round(float(current_raw.get("temp", 0)), 1),
            feels_like_c=round(float(current_raw.get("feels_like", 0)), 1),
            humidity_pct=round(float(current_raw.get("humidity", 0)), 1),
            precipitation_mm=round(
                float(current_raw.get("rain", {}).get("1h", 0) or
                      current_raw.get("snow", {}).get("1h", 0)), 2
            ),
            wind_speed_kmh=round(float(current_raw.get("wind_speed", 0)) * 3.6, 1),
            wind_direction_deg=int(current_raw.get("wind_deg", 0)),
            weather_code=weather.get("id", 800),
            description=weather.get("description", "").capitalize(),
            icon=_icon_slug(icon_code),
            source="openweather",
        )
        current.__dict__["uv_index"] = current_raw.get("uvi")

    return daily_points, current