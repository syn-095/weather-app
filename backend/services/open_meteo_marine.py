import requests
from datetime import datetime, timezone
from models.weather import HourlyPoint, DailyPoint

BASE_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: ("Clear sky", "clear"),
    1: ("Mainly clear", "partly-cloudy"),
    2: ("Partly cloudy", "partly-cloudy"),
    3: ("Overcast", "cloudy"),
    45: ("Foggy", "fog"),
    48: ("Icy fog", "fog"),
    51: ("Light drizzle", "drizzle"),
    53: ("Moderate drizzle", "drizzle"),
    55: ("Dense drizzle", "drizzle"),
    61: ("Slight rain", "rain"),
    63: ("Moderate rain", "rain"),
    65: ("Heavy rain", "rain"),
    71: ("Slight snow", "snow"),
    73: ("Moderate snow", "snow"),
    75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Slight showers", "showers"),
    81: ("Moderate showers", "showers"),
    82: ("Violent showers", "showers"),
    85: ("Snow showers", "snow"),
    86: ("Heavy snow showers", "snow"),
    95: ("Thunderstorm", "thunder"),
    96: ("Thunderstorm w/ hail", "thunder"),
    99: ("Thunderstorm w/ heavy hail", "thunder"),
}

def _code_info(code: int):
    return WMO_CODES.get(code, ("Unknown", "unknown"))

def fetch_forecast(lat: float, lon: float, days: int = 7) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
            "wind_direction_10m",
            "weathercode",
        ],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "wind_speed_10m_max",
            "weathercode",
            "sunrise",
            "sunset",
        ],
        "current_weather": True,
        "forecast_days": days,
        "timezone": "auto",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "temperature_unit": "celsius",
    }
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def normalize(raw: dict):
    hourly = raw.get("hourly", {})
    daily = raw.get("daily", {})
    current_raw = raw.get("current_weather", {})

    h_times = hourly.get("time", [])
    h_temp = hourly.get("temperature_2m", [])
    h_feels = hourly.get("apparent_temperature", [])
    h_humid = hourly.get("relative_humidity_2m", [])
    h_precip = hourly.get("precipitation", [])
    h_wind = hourly.get("wind_speed_10m", [])
    h_wind_dir = hourly.get("wind_direction_10m", [])
    h_code = hourly.get("weathercode", [])

    hourly_by_date = {}
    for i, t in enumerate(h_times):
        date_str = t[:10]
        desc, icon = _code_info(int(h_code[i]) if h_code[i] is not None else 0)
        hp = HourlyPoint(
            time=t,
            temperature_c=round(float(h_temp[i] or 0), 1),
            feels_like_c=round(float(h_feels[i] or 0), 1) if h_feels else None,
            humidity_pct=round(float(h_humid[i] or 0), 1),
            precipitation_mm=round(float(h_precip[i] or 0), 2),
            wind_speed_kmh=round(float(h_wind[i] or 0), 1),
            wind_direction_deg=int(h_wind_dir[i]) if h_wind_dir and h_wind_dir[i] is not None else None,
            weather_code=int(h_code[i]) if h_code[i] is not None else 0,
            description=desc,
            icon=icon,
            source="open_meteo",
        )
        hourly_by_date.setdefault(date_str, []).append(hp)

    d_dates = daily.get("time", [])
    d_max = daily.get("temperature_2m_max", [])
    d_min = daily.get("temperature_2m_min", [])
    d_precip = daily.get("precipitation_sum", [])
    d_wind_max = daily.get("wind_speed_10m_max", [])
    d_code = daily.get("weathercode", [])
    d_sunrise = daily.get("sunrise", [])
    d_sunset = daily.get("sunset", [])

    daily_points = []
    for i, date_str in enumerate(d_dates):
        hrs = hourly_by_date.get(date_str, [])
        avg_temp = round((float(d_max[i] or 0) + float(d_min[i] or 0)) / 2, 1)
        avg_humid = round(sum(h.humidity_pct for h in hrs) / len(hrs), 1) if hrs else 0.0
        avg_wind = round(sum(h.wind_speed_kmh for h in hrs) / len(hrs), 1) if hrs else 0.0
        code = int(d_code[i]) if d_code[i] is not None else 0
        desc, icon = _code_info(code)

        dp = DailyPoint(
            date=date_str,
            temp_max_c=round(float(d_max[i] or 0), 1),
            temp_min_c=round(float(d_min[i] or 0), 1),
            temp_avg_c=avg_temp,
            precipitation_mm=round(float(d_precip[i] or 0), 2),
            humidity_avg_pct=avg_humid,
            wind_max_kmh=round(float(d_wind_max[i] or 0), 1),
            wind_avg_kmh=avg_wind,
            weather_code=code,
            description=desc,
            icon=icon,
            sunrise=d_sunrise[i] if d_sunrise else None,
            sunset=d_sunset[i] if d_sunset else None,
            source="open_meteo",
            hourly=hrs,
        )
        daily_points.append(dp)

    # ── Current: use current_weather block for temp/wind,
    #    but pull feels_like & humidity from the closest hourly point ──
    current = None
    if current_raw:
        code = int(current_raw.get("weathercode", 0))
        desc, icon = _code_info(code)

        # Find the hourly entry whose time is closest to current_weather time
        current_time_str = current_raw.get("time", "")
        feels_like = None
        humidity = 0.0
        closest_hourly = None
        if current_time_str and h_times:
            # current_time_str format: "2024-06-01T14:00"
            # find the exact or nearest match
            for i, t in enumerate(h_times):
                if t[:13] == current_time_str[:13]:
                    feels_like = round(float(h_feels[i] or 0), 1) if h_feels and h_feels[i] is not None else None
                    humidity = round(float(h_humid[i] or 0), 1) if h_humid and h_humid[i] is not None else 0.0
                    break

        current = HourlyPoint(
            time=current_time_str or datetime.now(timezone.utc).isoformat(),
            temperature_c=round(float(current_raw.get("temperature", 0)), 1),
            feels_like_c=feels_like,
            humidity_pct=humidity,
            precipitation_mm=0.0,
            wind_speed_kmh=round(float(current_raw.get("windspeed", 0)), 1),
            wind_direction_deg=int(current_raw.get("winddirection", 0)),
            weather_code=code,
            description=desc,
            icon=icon,
            source="open_meteo",
        )

    return daily_points, current