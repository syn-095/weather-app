"""
services/pirate_weather.py
Fetches weather from Pirate Weather (10,000 calls/month free tier).
Drop-in Dark Sky replacement.
Docs: https://pirateweather.net/en/latest/
"""

import os
import requests
from datetime import datetime, timezone
from models.weather import HourlyPoint, DailyPoint

BASE_URL = "https://api.pirateweather.net/forecast"

def _get_key():
    key = os.getenv("PIRATE_WEATHER_API_KEY", "")
    if not key:
        raise EnvironmentError("PIRATE_WEATHER_API_KEY not set.")
    return key

PW_ICONS = {
    "clear-day": "clear",
    "clear-night": "clear",
    "partly-cloudy-day": "partly-cloudy",
    "partly-cloudy-night": "partly-cloudy",
    "cloudy": "cloudy",
    "fog": "fog",
    "wind": "partly-cloudy",
    "rain": "rain",
    "drizzle": "drizzle",
    "snow": "snow",
    "sleet": "drizzle",
    "thunderstorm": "thunder",
}

def fetch_forecast(lat: float, lon: float) -> dict:
    key = _get_key()
    url = f"{BASE_URL}/{key}/{lat},{lon}"
    params = {"units": "si", "extend": "hourly"}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def normalize(raw: dict):
    hourly_raw  = raw.get("hourly",  {}).get("data", [])
    daily_raw   = raw.get("daily",   {}).get("data", [])
    current_raw = raw.get("currently", {})

    hourly_by_date = {}
    for h in hourly_raw:
        dt = datetime.fromtimestamp(h["time"], tz=timezone.utc)
        time_str = dt.strftime("%Y-%m-%dT%H:%M")
        date_str = time_str[:10]
        icon = PW_ICONS.get(h.get("icon", ""), "unknown")

        hp = HourlyPoint(
            time=time_str,
            temperature_c=round(float(h.get("temperature", 0)), 1),
            feels_like_c=round(float(h.get("apparentTemperature", 0)), 1),
            humidity_pct=round(float(h.get("humidity", 0)) * 100, 1),
            precipitation_mm=round(float(h.get("precipIntensity", 0)), 2),
            wind_speed_kmh=round(float(h.get("windSpeed", 0)) * 3.6, 1),
            wind_direction_deg=int(h.get("windBearing", 0)),
            weather_code=0,
            description=h.get("summary", ""),
            icon=icon,
            source="pirate_weather",
        )
        hp.__dict__["precipitation_probability"] = round(
            float(h.get("precipProbability", 0)) * 100, 1
        )
        hp.__dict__["uv_index"] = h.get("uvIndex")
        hourly_by_date.setdefault(date_str, []).append(hp)

    daily_points = []
    for d in daily_raw:
        dt = datetime.fromtimestamp(d["time"], tz=timezone.utc)
        date_str = dt.strftime("%Y-%m-%d")
        icon = PW_ICONS.get(d.get("icon", ""), "unknown")
        hrs  = hourly_by_date.get(date_str, [])

        sunrise_str = datetime.fromtimestamp(
            d.get("sunriseTime", 0), tz=timezone.utc
        ).strftime("%H:%M") if d.get("sunriseTime") else None
        sunset_str = datetime.fromtimestamp(
            d.get("sunsetTime", 0), tz=timezone.utc
        ).strftime("%H:%M") if d.get("sunsetTime") else None

        dp = DailyPoint(
            date=date_str,
            temp_max_c=round(float(d.get("temperatureHigh", 0)), 1),
            temp_min_c=round(float(d.get("temperatureLow",  0)), 1),
            temp_avg_c=round(
                (float(d.get("temperatureHigh", 0)) +
                 float(d.get("temperatureLow",  0))) / 2, 1
            ),
            precipitation_mm=round(float(d.get("precipIntensity", 0)) * 24, 2),
            humidity_avg_pct=round(float(d.get("humidity", 0)) * 100, 1),
            wind_max_kmh=round(float(d.get("windGust",  0)) * 3.6, 1),
            wind_avg_kmh=round(float(d.get("windSpeed", 0)) * 3.6, 1),
            weather_code=0,
            description=d.get("summary", ""),
            icon=icon,
            sunrise=sunrise_str,
            sunset=sunset_str,
            source="pirate_weather",
            hourly=hrs,
        )
        daily_points.append(dp)

    current = None
    if current_raw:
        icon = PW_ICONS.get(current_raw.get("icon", ""), "unknown")
        dt = datetime.fromtimestamp(current_raw.get("time", 0), tz=timezone.utc)
        current = HourlyPoint(
            time=dt.strftime("%Y-%m-%dT%H:%M"),
            temperature_c=round(float(current_raw.get("temperature", 0)), 1),
            feels_like_c=round(float(current_raw.get("apparentTemperature", 0)), 1),
            humidity_pct=round(float(current_raw.get("humidity", 0)) * 100, 1),
            precipitation_mm=round(float(current_raw.get("precipIntensity", 0)), 2),
            wind_speed_kmh=round(float(current_raw.get("windSpeed", 0)) * 3.6, 1),
            wind_direction_deg=int(current_raw.get("windBearing", 0)),
            weather_code=0,
            description=current_raw.get("summary", ""),
            icon=icon,
            source="pirate_weather",
        )
        current.__dict__["uv_index"] = current_raw.get("uvIndex")

    return daily_points, current