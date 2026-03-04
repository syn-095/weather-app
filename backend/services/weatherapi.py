import os
import requests
from datetime import datetime
from models.weather import HourlyPoint, DailyPoint

BASE_URL = "https://api.weatherapi.com/v1"

def _get_key():
    key = os.getenv("WEATHERAPI_KEY", "")
    if not key:
        raise EnvironmentError("WEATHERAPI_KEY not set.")
    return key

def fetch_forecast(lat: float, lon: float, days: int = 7) -> dict:
    key = _get_key()
    params = {
        "key": key,
        "q": f"{lat},{lon}",
        "days": min(days, 10),
        "aqi": "no",
        "alerts": "no",
    }
    resp = requests.get(f"{BASE_URL}/forecast.json", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def normalize(raw: dict):
    forecast_days = raw.get("forecast", {}).get("forecastday", [])
    current_raw = raw.get("current", {})
    daily_points = []

    for fd in forecast_days:
        date_str = fd["date"]
        day = fd.get("day", {})
        astro = fd.get("astro", {})
        hour_list = fd.get("hour", [])

        hourly = []
        for h in hour_list:
            cond = h.get("condition", {})
            hp = HourlyPoint(
                time=h["time"].replace(" ", "T"),
                temperature_c=round(float(h.get("temp_c", 0)), 1),
                feels_like_c=round(float(h.get("feelslike_c", 0)), 1),
                humidity_pct=round(float(h.get("humidity", 0)), 1),
                precipitation_mm=round(float(h.get("precip_mm", 0)), 2),
                wind_speed_kmh=round(float(h.get("wind_kph", 0)), 1),
                wind_direction_deg=int(h.get("wind_degree", 0)),
                weather_code=int(cond.get("code", 1000)),
                description=cond.get("text", ""),
                icon=cond.get("icon", "").split("/")[-1].replace(".png", ""),
                source="weatherapi",
            )
            hourly.append(hp)

        avg_wind = round(sum(h.wind_speed_kmh for h in hourly) / len(hourly), 1) if hourly else 0.0
        cond = day.get("condition", {})
        dp = DailyPoint(
            date=date_str,
            temp_max_c=round(float(day.get("maxtemp_c", 0)), 1),
            temp_min_c=round(float(day.get("mintemp_c", 0)), 1),
            temp_avg_c=round(float(day.get("avgtemp_c", 0)), 1),
            precipitation_mm=round(float(day.get("totalprecip_mm", 0)), 2),
            humidity_avg_pct=round(float(day.get("avghumidity", 0)), 1),
            wind_max_kmh=round(float(day.get("maxwind_kph", 0)), 1),
            wind_avg_kmh=avg_wind,
            weather_code=int(cond.get("code", 1000)),
            description=cond.get("text", ""),
            icon=cond.get("icon", "").split("/")[-1].replace(".png", ""),
            sunrise=astro.get("sunrise"),
            sunset=astro.get("sunset"),
            source="weatherapi",
            hourly=hourly,
        )
        daily_points.append(dp)

    current = None
    if current_raw:
        cond = current_raw.get("condition", {})
        current = HourlyPoint(
            time=datetime.now().isoformat(timespec="minutes"),
            temperature_c=round(float(current_raw.get("temp_c", 0)), 1),
            feels_like_c=round(float(current_raw.get("feelslike_c", 0)), 1),
            humidity_pct=round(float(current_raw.get("humidity", 0)), 1),
            precipitation_mm=round(float(current_raw.get("precip_mm", 0)), 2),
            wind_speed_kmh=round(float(current_raw.get("wind_kph", 0)), 1),
            wind_direction_deg=int(current_raw.get("wind_degree", 0)),
            weather_code=int(cond.get("code", 1000)),
            description=cond.get("text", ""),
            icon=cond.get("icon", "").split("/")[-1].replace(".png", ""),
            source="weatherapi",
        )

    return daily_points, current