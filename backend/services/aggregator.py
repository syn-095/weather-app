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
import services.tomorrow_io as tomorrow_io
import services.openweather as openweather
import services.visual_crossing as visual_crossing
import services.pirate_weather as pirate_weather

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
                feels_vals   = [h.feels_like_c for h in hs if h.feels_like_c is not None]
                precip_probs = [h.__dict__.get("precipitation_probability")
                                for h in hs
                                if h.__dict__.get("precipitation_probability") is not None]
                uv_vals      = [h.__dict__.get("uv_index")
                                for h in hs
                                if h.__dict__.get("uv_index") is not None]
                merged_hourly.append({
                    "time": hs[0].time,
                    "temperature_c": _avg(*[h.temperature_c for h in hs]),
                    "feels_like_c": _avg(*feels_vals) if feels_vals else None,
                    "humidity_pct": _avg(*[h.humidity_pct for h in hs]),
                    "precipitation_mm": _avg(*[h.precipitation_mm for h in hs]),
                    "precipitation_probability": _avg(*precip_probs) if precip_probs else None,
                    "wind_speed_kmh": _avg(*[h.wind_speed_kmh for h in hs]),
                    "wind_direction_deg": hs[0].wind_direction_deg,
                    "weather_code": hs[0].weather_code,
                    "description": hs[0].description,
                    "icon": hs[0].icon,
                    "uv_index": _avg(*uv_vals) if uv_vals else None,
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

    feels_vals    = [c.feels_like_c for c in valid if c.feels_like_c is not None]
    humidity_vals = [c.humidity_pct for c in valid if c.humidity_pct and c.humidity_pct > 0]
    uv_vals       = [c.__dict__.get("uv_index") for c in valid
                     if c.__dict__.get("uv_index") is not None]

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
        "uv_index": _avg(*uv_vals) if uv_vals else None,
        "source": "aggregated",
    }


def _try_source(name, fn, all_daily, all_currents, sources_used, errors):
    """Helper to call a source and handle failures gracefully."""
    try:
        daily, current = fn()
        all_daily.append(daily)
        all_currents.append(current)
        sources_used.append(name)
        logger.info("%s: %d days fetched", name, len(daily))
    except EnvironmentError:
        logger.info("%s: API key not configured – skipping", name)
    except Exception as exc:
        logger.warning("%s failed: %s", name, exc)
        errors.append(f"{name}: {exc}")


def get_weather(lat, lon, location_name="", days=7):
    cache_key = f"{round(lat, 3)}:{round(lon, 3)}:{days}"
    if cache_key in _cache:
        return _cache[cache_key]

    all_daily, all_currents, sources_used, errors = [], [], [], []

    _try_source("open_meteo",     lambda: open_meteo.normalize(open_meteo.fetch_forecast(lat, lon, days)),         all_daily, all_currents, sources_used, errors)
    _try_source("yr_no",          lambda: yr_no.normalize(yr_no.fetch_forecast(lat, lon)),                         all_daily, all_currents, sources_used, errors)
    _try_source("weatherapi",     lambda: weatherapi_svc.normalize(weatherapi_svc.fetch_forecast(lat, lon, days)), all_daily, all_currents, sources_used, errors)
    _try_source("tomorrow_io",    lambda: tomorrow_io.normalize(tomorrow_io.fetch_forecast(lat, lon, days)),        all_daily, all_currents, sources_used, errors)
    _try_source("openweather",    lambda: openweather.normalize(openweather.fetch_forecast(lat, lon)),              all_daily, all_currents, sources_used, errors)
    _try_source("visual_crossing",lambda: visual_crossing.normalize(visual_crossing.fetch_forecast(lat, lon, days)),all_daily, all_currents, sources_used, errors)
    _try_source("pirate_weather", lambda: pirate_weather.normalize(pirate_weather.fetch_forecast(lat, lon)),        all_daily, all_currents, sources_used, errors)

    if not all_daily:
        raise RuntimeError(f"All weather sources failed: {'; '.join(errors)}")

    # Supplemental sources
    air_data, marine_data, climate_data = None, None, None

    try:
        air_data = air_quality.normalize(air_quality.fetch_air_quality(lat, lon))
        sources_used.append("open_meteo_air")
    except Exception as exc:
        logger.warning("Air quality failed: %s", exc)

    try:
        raw_marine = marine.fetch_forecast(lat, lon, days)
        if marine.is_available(raw_marine):
            marine_data = marine.normalize(raw_marine)
            sources_used.append("open_meteo_marine")
    except Exception as exc:
        logger.warning("Marine failed: %s", exc)

    try:
        climate_data = climate.normalize(climate.fetch_climate_normals(lat, lon))
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