"""
services/tomorrow_io.py
Fetches weather from Tomorrow.io API (500 calls/day free tier).
Docs: https://docs.tomorrow.io/reference/weather-forecast
"""

import os
import requests
from datetime import datetime
from models.weather import HourlyPoint, DailyPoint

BASE_URL = "https://api.tomorrow.io/v4/weather/forecast"

def _get_key():
    key = os.getenv("TOMORROW_API_KEY", "")
    if not key:
        raise EnvironmentError("TOMORROW_API_KEY not set.")
    return key

# Tomorrow.io weather codes → (description, icon slug)
WEATHER_CODES = {
    1000: ("Clear sky", "clear"),
    1100: ("Mostly clear", "partly-cloudy"),
    1101: ("Partly cloudy", "partly-cloudy"),
    1102: ("Mostly cloudy", "cloudy"),
    1001: ("Cloudy", "cloudy"),
    2000: ("Fog", "fog"),
    2100: ("Light fog", "fog"),
    4000: ("Drizzle", "drizzle"),
    4001: ("Rain", "rain"),
    4200: ("Light rain", "rain"),
    4201: ("Heavy rain", "rain"),
    5000: ("Snow", "snow"),
    5001: ("Flurries", "snow"),
    5100: ("Light snow", "snow"),
    5101: ("Heavy snow", "snow"),
    6000: ("Freezing drizzle", "drizzle"),
    6001: ("Freezing rain", "rain"),
    6200: ("Light freezing rain", "rain"),
    6201: ("Heavy freezing rain", "rain"),
    7000: ("Ice pellets", "snow"),
    7101: ("Heavy ice pellets", "snow"),
    7102: ("Light ice pellets", "snow"),
    8000: ("Thunderstorm", "thunder"),
}

def _code_info(code):
    return WEATHER_CODES.get(code, ("Unknown", "unknown"))

def fetch_forecast(lat: float, lon: float, days: int = 7) -> dict:
    key = _get_key()
    params = {
        "location": f"{lat},{lon}",
        "apikey": key,
        "units": "metric",
        "timesteps": ["1h", "1d"],
        "fields": [
            "temperature", "apparentTemperature", "humidity",
            "precipitationIntensity", "precipitationProbability",
            "windSpeed", "windDirection", "weatherCode",
            "uvIndex", "cloudCover", "visibility",
            "temperatureMax", "temperatureMin", "temperatureAvg",
            "windSpeedAvg", "precipitationAccumulation",
            "sunriseTime", "sunsetTime",
        ],
    }
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def normalize(raw: dict):
    timelines = raw.get("timelines", {})
    hourly_data = timelines.get("hourly", [])
    daily_data  = timelines.get("daily",  [])

    # Build hourly points grouped by date
    hourly_by_date = {}
    for entry in hourly_data:
        time_str = entry.get("time", "")[:16].replace("Z", "")
        date_str = time_str[:10]
        vals = entry.get("values", {})
        code = int(vals.get("weatherCode", 1000))
        desc, icon = _code_info(code)

        hp = HourlyPoint(
            time=time_str,
            temperature_c=round(float(vals.get("temperature", 0)), 1),
            feels_like_c=round(float(vals.get("apparentTemperature", 0)), 1),
            humidity_pct=round(float(vals.get("humidity", 0)), 1),
            precipitation_mm=round(float(vals.get("precipitationIntensity", 0)), 2),
            wind_speed_kmh=round(float(vals.get("windSpeed", 0)) * 3.6, 1),
            wind_direction_deg=int(vals.get("windDirection", 0)),
            weather_code=code,
            description=desc,
            icon=icon,
            source="tomorrow_io",
        )
        hp.__dict__["precipitation_probability"] = round(
            float(vals.get("precipitationProbability", 0)), 1
        )
        hp.__dict__["uv_index"]    = vals.get("uvIndex")
        hp.__dict__["cloud_cover"] = vals.get("cloudCover")
        hourly_by_date.setdefault(date_str, []).append(hp)

    # Build daily points
    daily_points = []
    for entry in daily_data:
        date_str = entry.get("time", "")[:10]
        vals = entry.get("values", {})
        code = int(vals.get("weatherCodeMax", 1000))
        desc, icon = _code_info(code)
        hrs = hourly_by_date.get(date_str, [])

        dp = DailyPoint(
            date=date_str,
            temp_max_c=round(float(vals.get("temperatureMax", 0)), 1),
            temp_min_c=round(float(vals.get("temperatureMin", 0)), 1),
            temp_avg_c=round(float(vals.get("temperatureAvg", 0)), 1),
            precipitation_mm=round(float(vals.get("precipitationAccumulationAvg", 0)), 2),
            humidity_avg_pct=round(
                sum(h.humidity_pct for h in hrs) / len(hrs), 1
            ) if hrs else 0.0,
            wind_max_kmh=round(float(vals.get("windSpeedMax", 0)) * 3.6, 1),
            wind_avg_kmh=round(float(vals.get("windSpeedAvg", 0)) * 3.6, 1),
            weather_code=code,
            description=desc,
            icon=icon,
            sunrise=vals.get("sunriseTime", "")[:16],
            sunset=vals.get("sunsetTime",  "")[:16],
            source="tomorrow_io",
            hourly=hrs,
        )
        daily_points.append(dp)

    current = hourly_by_date.get(
        sorted(hourly_by_date.keys())[0], []
    )[0] if hourly_by_date else None

    return daily_points, current