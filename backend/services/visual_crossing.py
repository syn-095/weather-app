"""
services/visual_crossing.py
Fetches weather from Visual Crossing (1000 calls/day free tier).
Docs: https://www.visualcrossing.com/resources/documentation/weather-api
"""

import os
import requests
from models.weather import HourlyPoint, DailyPoint

BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

def _get_key():
    key = os.getenv("VISUALCROSSING_API_KEY", "")
    if not key:
        raise EnvironmentError("VISUALCROSSING_API_KEY not set.")
    return key

VC_ICONS = {
    "clear-day": "clear",
    "clear-night": "clear",
    "partly-cloudy-day": "partly-cloudy",
    "partly-cloudy-night": "partly-cloudy",
    "cloudy": "cloudy",
    "fog": "fog",
    "wind": "partly-cloudy",
    "rain": "rain",
    "drizzle": "drizzle",
    "showers-day": "showers",
    "showers-night": "showers",
    "snow": "snow",
    "snow-showers-day": "snow",
    "snow-showers-night": "snow",
    "sleet": "drizzle",
    "thunder-rain": "thunder",
    "thunder-showers-day": "thunder",
    "thunder-showers-night": "thunder",
}

def fetch_forecast(lat: float, lon: float, days: int = 7) -> dict:
    key = _get_key()
    url = f"{BASE_URL}/{lat},{lon}"
    params = {
        "key": key,
        "unitGroup": "metric",
        "include": "hours,days,current",
        "contentType": "json",
        "iconSet": "icons2",
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def normalize(raw: dict):
    days_raw    = raw.get("days", [])
    current_raw = raw.get("currentConditions", {})

    hourly_by_date = {}
    daily_points   = []

    for day in days_raw:
        date_str = day.get("datetime", "")
        hours    = day.get("hours", [])

        hourly = []
        for h in hours:
            time_str = f"{date_str}T{h.get('datetime', '00:00:00')[:5]}"
            icon = VC_ICONS.get(h.get("icon", ""), "unknown")
            hp = HourlyPoint(
                time=time_str,
                temperature_c=round(float(h.get("temp", 0)), 1),
                feels_like_c=round(float(h.get("feelslike", 0)), 1),
                humidity_pct=round(float(h.get("humidity", 0)), 1),
                precipitation_mm=round(float(h.get("precip", 0) or 0), 2),
                wind_speed_kmh=round(float(h.get("windspeed", 0)), 1),
                wind_direction_deg=int(h.get("winddir", 0)),
                weather_code=0,
                description=h.get("conditions", ""),
                icon=icon,
                source="visual_crossing",
            )
            hp.__dict__["precipitation_probability"] = round(
                float(h.get("precipprob", 0)), 1
            )
            hp.__dict__["uv_index"] = h.get("uvindex")
            hourly.append(hp)
            hourly_by_date.setdefault(date_str, []).append(hp)

        icon = VC_ICONS.get(day.get("icon", ""), "unknown")
        dp = DailyPoint(
            date=date_str,
            temp_max_c=round(float(day.get("tempmax", 0)), 1),
            temp_min_c=round(float(day.get("tempmin", 0)), 1),
            temp_avg_c=round(float(day.get("temp", 0)), 1),
            precipitation_mm=round(float(day.get("precip", 0) or 0), 2),
            humidity_avg_pct=round(float(day.get("humidity", 0)), 1),
            wind_max_kmh=round(float(day.get("windgust", 0) or 0), 1),
            wind_avg_kmh=round(float(day.get("windspeed", 0)), 1),
            weather_code=0,
            description=day.get("conditions", ""),
            icon=icon,
            sunrise=day.get("sunrise", "")[:5] if day.get("sunrise") else None,
            sunset=day.get("sunset",  "")[:5] if day.get("sunset")  else None,
            source="visual_crossing",
            hourly=hourly,
        )
        daily_points.append(dp)

    # Current
    current = None
    if current_raw:
        icon = VC_ICONS.get(current_raw.get("icon", ""), "unknown")
        current = HourlyPoint(
            time=current_raw.get("datetime", ""),
            temperature_c=round(float(current_raw.get("temp", 0)), 1),
            feels_like_c=round(float(current_raw.get("feelslike", 0)), 1),
            humidity_pct=round(float(current_raw.get("humidity", 0)), 1),
            precipitation_mm=round(float(current_raw.get("precip", 0) or 0), 2),
            wind_speed_kmh=round(float(current_raw.get("windspeed", 0)), 1),
            wind_direction_deg=int(current_raw.get("winddir", 0)),
            weather_code=0,
            description=current_raw.get("conditions", ""),
            icon=icon,
            source="visual_crossing",
        )
        current.__dict__["uv_index"] = current_raw.get("uvindex")

    return daily_points, current