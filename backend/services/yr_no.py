"""
services/yr_no.py
Fetches weather from Yr.no (Norwegian Meteorological Institute).
No API key required. Must include a User-Agent per their terms.
Docs: https://api.met.no/weatherapi/locationforecast/2.0/documentation
"""

import requests
from datetime import datetime
from models.weather import HourlyPoint, DailyPoint

BASE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"

# Required by Yr.no terms of service
HEADERS = {
    "User-Agent": "WeatherAgg/1.0 github.com/yourusername/weatheragg"
}

# Yr.no symbol codes → our icon slugs
SYMBOL_MAP = {
    "clearsky": "clear",
    "fair": "partly-cloudy",
    "partlycloudy": "partly-cloudy",
    "cloudy": "cloudy",
    "fog": "fog",
    "lightrain": "drizzle",
    "rain": "rain",
    "heavyrain": "rain",
    "lightrainshowers": "showers",
    "rainshowers": "showers",
    "heavyrainshowers": "showers",
    "lightsleet": "drizzle",
    "sleet": "drizzle",
    "heavysleet": "rain",
    "lightsnow": "snow",
    "snow": "snow",
    "heavysnow": "snow",
    "lightsnowshowers": "snow",
    "snowshowers": "snow",
    "heavysnowshowers": "snow",
    "thunderstorm": "thunder",
    "rainandthunder": "thunder",
    "snowandthunder": "thunder",
}


def _map_symbol(symbol: str) -> tuple:
    if not symbol:
        return "Unknown", "unknown"
    # Strip day/night suffix e.g. "clearsky_day" -> "clearsky"
    base = symbol.split("_")[0]
    icon = SYMBOL_MAP.get(base, "unknown")
    desc = base.replace("_", " ").capitalize()
    return desc, icon


def fetch_forecast(lat: float, lon: float) -> dict:
    params = {"lat": round(lat, 4), "lon": round(lon, 4)}
    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()


def normalize(raw: dict):
    """
    Returns (daily_list, current_hourly_point)
    """
    timeseries = raw.get("properties", {}).get("timeseries", [])
    if not timeseries:
        return [], None

    hourly_by_date = {}
    current = None

    for entry in timeseries:
        time_str = entry.get("time", "")
        # Convert to local-ish ISO format
        time_fmt = time_str.replace("Z", "").replace("+00:00", "")
        date_str = time_fmt[:10]

        instant = entry.get("data", {}).get("instant", {}).get("details", {})
        next1h = entry.get("data", {}).get("next_1_hours", {})
        next6h = entry.get("data", {}).get("next_6_hours", {})

        summary = next1h.get("summary", {}) or next6h.get("summary", {})
        symbol = summary.get("symbol_code", "")
        desc, icon = _map_symbol(symbol)

        details_1h = next1h.get("details", {})
        details_6h = next6h.get("details", {})

        precip = (
            details_1h.get("precipitation_amount")
            or details_6h.get("precipitation_amount")
            or 0.0
        )
        precip_prob = (
            details_1h.get("probability_of_precipitation")
            or details_6h.get("probability_of_precipitation")
            or 0.0
        )

        hp = HourlyPoint(
            time=time_fmt,
            temperature_c=round(float(instant.get("air_temperature", 0)), 1),
            feels_like_c=None,
            humidity_pct=round(float(instant.get("relative_humidity", 0)), 1),
            precipitation_mm=round(float(precip), 2),
            wind_speed_kmh=round(float(instant.get("wind_speed", 0)) * 3.6, 1),
            wind_direction_deg=int(instant.get("wind_from_direction", 0)),
            weather_code=0,
            description=desc,
            icon=icon,
            source="yr_no",
        )
        # Store precip_prob as extra attribute
        hp.__dict__["precipitation_probability"] = round(float(precip_prob), 1)

        hourly_by_date.setdefault(date_str, []).append(hp)

        if current is None:
            current = hp

    # Build daily summaries
    daily_points = []
    for date_str in sorted(hourly_by_date.keys()):
        hrs = hourly_by_date[date_str]
        temps = [h.temperature_c for h in hrs]
        daily_points.append(DailyPoint(
            date=date_str,
            temp_max_c=round(max(temps), 1),
            temp_min_c=round(min(temps), 1),
            temp_avg_c=round(sum(temps) / len(temps), 1),
            precipitation_mm=round(sum(h.precipitation_mm for h in hrs), 2),
            humidity_avg_pct=round(sum(h.humidity_pct for h in hrs) / len(hrs), 1),
            wind_max_kmh=round(max(h.wind_speed_kmh for h in hrs), 1),
            wind_avg_kmh=round(sum(h.wind_speed_kmh for h in hrs) / len(hrs), 1),
            weather_code=0,
            description=hrs[0].description,
            icon=hrs[0].icon,
            sunrise=None,
            sunset=None,
            source="yr_no",
            hourly=hrs,
        ))

    return daily_points, current