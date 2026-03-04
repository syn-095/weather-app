import os
import logging
from datetime import datetime, timezone
from cachetools import TTLCache
from models.weather import HourlyPoint, DailyPoint
import services.open_meteo as open_meteo
import services.weatherapi as weatherapi_svc
import services.yr_no as yr_no
import services.open_meteo_air as air_quality
import services.open_meteo_marine as marine
import services.open_meteo_climate as climate

logger = logging.getLogger(__name__)

CACHE_TTL = int(os.getenv("CACHE_TTL", 600))
_cache = TTLCache(maxsize=256, ttl=CACHE_TTL)


def _avg(*values):
    valid = [v for v in values if v is not None]
    return round(sum(valid) / len(valid), 1) if valid else None


def _merge_daily(sources):
    by_date = {}
    for source_days in sources:
        for dp in source_days:
            by_date.setdefault(dp.date, []).append(dp)

    merged = []
    for date_str in sorted(by_date.keys()):
        days = by_date[date_str]
        sunrise = next((d.sunrise for d in days if d.sunrise), None)
        sunset  = next((d.sunset  for d in days if d.sunset),  None)

        all_hourly = []
        for d in days:
            all_hourly.extend(d.hourly)

        hourly_by_hour = {}
        for h in all_hourly:
            key = h.time[:13]
            hourly_by_hour.setdefault(key, []).append(h)

        merged_hourly = []
        for key in sorted(hourly_by_hour.keys()):
            hs = hourly_by_hour[key]
            if len(hs) == 1:
                merged_hourly.append(hs[0].to_dict())
            else:
                # For feels_like, only average sources that actually have it
                feels_vals = [h.feels_like_c for h in hs if h.feels_like_c is not None]
                merged_hourly.append({
                    "time": hs[0].time,
                    "temperature_c": _avg(*[h.temperature_c for h in hs]),
                    "feels_like_c": _avg(*feels_vals) if feels_vals else None,
                    "humidity_pct": _avg(*[h.humidity_pct for h in hs]),
                    "precipitation_mm": _avg(*[h.precipitation_mm for h in hs]),
                    "wind_speed_kmh": _avg(*[h.wind_speed_kmh for h in hs]),
                    "wind_direction_deg": hs[0].wind_direction_deg,
                    "weather_code": hs[0].weather_code,
                    "description": hs[0].description,
                    "icon": hs[0].icon,
                    "source": "aggregated",
                })

        merged.append({
            "date": date_str,
            "temp_max_c": _avg(*[d.temp_max_c for d in days]),
            "temp_min_c": _avg(*[d.temp_min_c for d in days]),
            "temp_avg_c": _avg(*[d.temp_avg_c for d in days]),
            "precipitation_mm": _avg(*[d.precipitation_mm for d in days]),
            "humidity_avg_pct": _avg(*[d.humidity_avg_pct for d in days]),
            "wind_max_kmh": _avg(*[d.wind_max_kmh for d in days]),
            "wind_avg_kmh": _avg(*[d.wind_avg_kmh for d in days]),
            "weather_code": days[0].weather_code,
            "description": days[0].description,
            "icon": days[0].icon,
            "sunrise": sunrise,
            "sunset": sunset,
            "sources": [d.source for d in days],
            "hourly": merged_hourly,
        })

    return merged


def _merge_current(currents):
    valid = [c for c in currents if c is not None]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0].to_dict()

    # Prefer feels_like_c from sources that actually provide it
    feels_vals = [c.feels_like_c for c in valid if c.feels_like_c is not None]
    humidity_vals = [c.humidity_pct for c in valid if c.humidity_pct and c.humidity_pct > 0]

    return {
        "time": valid[0].time,
        "temperature_c": _avg(*[c.temperature_c for c in valid]),
        "feels_like_c": _avg(*feels_vals) if feels_vals else None,
        "humidity_pct": _avg(*humidity_vals) if humidity_vals else 0.0,
        "precipitation_mm": _avg(*[c.precipitation_mm for c in valid]),
        "wind_speed_kmh": _avg(*[c.wind_speed_kmh for c in valid]),
        "wind_direction_deg": valid[0].wind_direction_deg,
        "weather_code": valid[0].weather_code,
        "description": valid[0].description,
        "icon": valid[0].icon,
        "source": "aggregated",
    }


def get_weather(lat, lon, location_name="", days=7):
    cache_key = f"{round(lat, 3)}:{round(lon, 3)}:{days}"
    if cache_key in _cache:
        return _cache[cache_key]

    all_daily, all_currents, sources_used, errors = [], [], [], []

    try:
        raw_om = open_meteo.fetch_forecast(lat, lon, days)
        om_daily, om_current = open_meteo.normalize(raw_om)
        all_daily.append(om_daily)
        all_currents.append(om_current)
        sources_used.append("open_meteo")
    except Exception as exc:
        logger.warning("Open-Meteo failed: %s", exc)
        errors.append(f"open_meteo: {exc}")

    try:
        raw_wa = weatherapi_svc.fetch_forecast(lat, lon, days)
        wa_daily, wa_current = weatherapi_svc.normalize(raw_wa)
        all_daily.append(wa_daily)
        all_currents.append(wa_current)
        sources_used.append("weatherapi")
    except EnvironmentError:
        logger.info("WeatherAPI key not configured – skipping")
    except Exception as exc:
        logger.warning("WeatherAPI failed: %s", exc)
        errors.append(f"weatherapi: {exc}")

    try:
        raw_yr = yr_no.fetch_forecast(lat, lon)
        yr_daily, yr_current = yr_no.normalize(raw_yr)
        all_daily.append(yr_daily)
        all_currents.append(yr_current)
        sources_used.append("yr_no")
    except Exception as exc:
        logger.warning("Yr.no failed: %s", exc)
        errors.append(f"yr_no: {exc}")

    if not all_daily:
        raise RuntimeError(f"All weather sources failed: {'; '.join(errors)}")

    air_data = None
    try:
        raw_air = air_quality.fetch_air_quality(lat, lon)
        air_data = air_quality.normalize(raw_air)
        sources_used.append("open_meteo_air")
    except Exception as exc:
        logger.warning("Air quality failed: %s", exc)

    marine_data = None
    try:
        raw_marine = marine.fetch_marine(lat, lon, days)
        if marine.is_available(raw_marine):
            marine_data = marine.normalize(raw_marine)
            sources_used.append("open_meteo_marine")
    except Exception as exc:
        logger.warning("Marine failed: %s", exc)

    climate_data = None
    try:
        raw_climate = climate.fetch_climate_normals(lat, lon)
        climate_data = climate.normalize(raw_climate)
        sources_used.append("open_meteo_climate")
    except Exception as exc:
        logger.warning("Climate failed: %s", exc)

    result = {
        "location": location_name,
        "latitude": lat,
        "longitude": lon,
        "current": _merge_current(all_currents),
        "aggregated_daily": _merge_daily(all_daily),
        "air_quality": air_data,
        "marine": marine_data,
        "climate_normals": climate_data,
        "sources": sources_used,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "errors": errors,
    }

    _cache[cache_key] = result
    return result