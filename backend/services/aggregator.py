import os
import logging
import threading
from datetime import date, datetime, timezone
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
import services.forecast_logger as forecast_logger
import services.actuals_fetcher as actuals_fetcher
import services.weight_loader as weight_loader

logger = logging.getLogger(__name__)

CACHE_TTL = int(os.getenv("CACHE_TTL", 600))
_cache = TTLCache(maxsize=256, ttl=CACHE_TTL)


# ── Aggregation helpers ───────────────────────────────────────────────────────

def _avg(*values):
    """Plain arithmetic mean — used for metrics with no weight data yet."""
    valid = [v for v in values if v is not None]
    return round(sum(valid) / len(valid), 1) if valid else None


def _weighted_avg(value_weight_pairs):
    """
    Weighted mean over (value, weight) pairs; None values are excluded.
    Falls back to equal weights when all weights are equal (optimisation).
    """
    valid = [(v, w) for v, w in value_weight_pairs if v is not None]
    if not valid:
        return None
    total_weight = sum(w for _, w in valid)
    if total_weight == 0:
        return _avg(*[v for v, _ in valid])
    return round(sum(v * w for v, w in valid) / total_weight, 1)


def _w(weights: dict, provider: str, metric: str) -> float:
    """Look up a provider's weight for a metric; default to 1.0."""
    return weights.get(provider, {}).get(metric, 1.0)


# ── Merge functions ───────────────────────────────────────────────────────────

def _merge_daily(named_sources: list, weights: dict) -> list:
    """
    named_sources: list of (provider_name, [DailyPoint, ...])
    weights:       dict from weight_loader.get_weights()
    """
    # Group DailyPoints by date, keeping track of provider name
    by_date: dict = {}
    for provider_name, daily_list in named_sources:
        for dp in daily_list:
            by_date.setdefault(dp.date, []).append((provider_name, dp))

    merged = []
    for date_str in sorted(by_date.keys()):
        named_days = by_date[date_str]   # list of (provider, DailyPoint)
        days       = [dp for _, dp in named_days]

        sunrise = next((d.sunrise for d in days if d.sunrise), None)
        sunset  = next((d.sunset  for d in days if d.sunset),  None)

        # Merge hourly: group all hourly points by hour key
        hourly_by_hour: dict = {}
        for provider_name, dp in named_days:
            for h in dp.hourly:
                key = h.time[:13]
                hourly_by_hour.setdefault(key, []).append((provider_name, h))

        merged_hourly = []
        for key in sorted(hourly_by_hour.keys()):
            named_hs = hourly_by_hour[key]
            if len(named_hs) == 1:
                merged_hourly.append(named_hs[0][1].to_dict())
            else:
                hs = [h for _, h in named_hs]
                feels_vals   = [(h.feels_like_c, _w(weights, pn, "temperature"))
                                for pn, h in named_hs if h.feels_like_c is not None]
                precip_probs = [(h.__dict__.get("precipitation_probability"),
                                 _w(weights, pn, "precipitation"))
                                for pn, h in named_hs
                                if h.__dict__.get("precipitation_probability") is not None]
                uv_vals      = [h.__dict__.get("uv_index") for h in hs
                                if h.__dict__.get("uv_index") is not None]
                merged_hourly.append({
                    "time":                    hs[0].time,
                    "temperature_c":           _weighted_avg([
                                                   (h.temperature_c, _w(weights, pn, "temperature"))
                                                   for pn, h in named_hs
                                               ]),
                    "feels_like_c":            _weighted_avg(feels_vals) if feels_vals else None,
                    "humidity_pct":            _avg(*[h.humidity_pct for h in hs]),
                    "precipitation_mm":        _weighted_avg([
                                                   (h.precipitation_mm, _w(weights, pn, "precipitation"))
                                                   for pn, h in named_hs
                                               ]),
                    "precipitation_probability": _weighted_avg(precip_probs) if precip_probs else None,
                    "wind_speed_kmh":          _weighted_avg([
                                                   (h.wind_speed_kmh, _w(weights, pn, "wind"))
                                                   for pn, h in named_hs
                                               ]),
                    "wind_direction_deg":      hs[0].wind_direction_deg,
                    "weather_code":            hs[0].weather_code,
                    "description":             hs[0].description,
                    "icon":                    hs[0].icon,
                    "uv_index":                _avg(*uv_vals) if uv_vals else None,
                    "source":                  "aggregated",
                })

        uv_vals = [dp.__dict__.get("uv_index") for dp in days
                   if dp.__dict__.get("uv_index") is not None]

        merged.append({
            "date":           date_str,
            "temp_max_c":     _weighted_avg([(dp.temp_max_c,       _w(weights, pn, "temperature"))   for pn, dp in named_days]),
            "temp_min_c":     _weighted_avg([(dp.temp_min_c,       _w(weights, pn, "temperature"))   for pn, dp in named_days]),
            "temp_avg_c":     _weighted_avg([(dp.temp_avg_c,       _w(weights, pn, "temperature"))   for pn, dp in named_days]),
            "precipitation_mm": _weighted_avg([(dp.precipitation_mm, _w(weights, pn, "precipitation")) for pn, dp in named_days]),
            "humidity_avg_pct": _avg(*[dp.humidity_avg_pct for dp in days]),
            "wind_max_kmh":   _weighted_avg([(dp.wind_max_kmh,     _w(weights, pn, "wind"))           for pn, dp in named_days]),
            "wind_avg_kmh":   _weighted_avg([(dp.wind_avg_kmh,     _w(weights, pn, "wind"))           for pn, dp in named_days]),
            "weather_code":   days[0].weather_code,
            "description":    days[0].description,
            "icon":           days[0].icon,
            "sunrise":        sunrise,
            "sunset":         sunset,
            "sources":        [dp.source for dp in days],
            "hourly":         merged_hourly,
        })

    return merged


def _merge_current(named_currents: list, weights: dict):
    """
    named_currents: list of (provider_name, HourlyPoint|None)
    """
    valid = [(pn, c) for pn, c in named_currents if c is not None]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0][1].to_dict()

    feels_vals    = [(c.feels_like_c,     _w(weights, pn, "temperature"))
                     for pn, c in valid if c.feels_like_c is not None]
    humidity_vals = [c.humidity_pct for _, c in valid if c.humidity_pct and c.humidity_pct > 0]
    uv_vals       = [c.__dict__.get("uv_index") for _, c in valid
                     if c.__dict__.get("uv_index") is not None]
    first_c = valid[0][1]

    return {
        "time":              first_c.time,
        "temperature_c":     _weighted_avg([(c.temperature_c,  _w(weights, pn, "temperature"))   for pn, c in valid]),
        "feels_like_c":      _weighted_avg(feels_vals) if feels_vals else None,
        "humidity_pct":      _avg(*humidity_vals) if humidity_vals else 0.0,
        "precipitation_mm":  _weighted_avg([(c.precipitation_mm, _w(weights, pn, "precipitation")) for pn, c in valid]),
        "wind_speed_kmh":    _weighted_avg([(c.wind_speed_kmh,  _w(weights, pn, "wind"))           for pn, c in valid]),
        "wind_direction_deg": first_c.wind_direction_deg,
        "weather_code":      first_c.weather_code,
        "description":       first_c.description,
        "icon":              first_c.icon,
        "uv_index":          _avg(*uv_vals) if uv_vals else None,
        "source":            "aggregated",
    }


# ── Source fetcher ────────────────────────────────────────────────────────────

def _try_source(name, fn, named_daily, named_currents, sources_used, errors):
    """Call a provider function and accumulate results; swallow failures gracefully."""
    try:
        daily, current = fn()
        named_daily.append((name, daily))
        named_currents.append((name, current))
        sources_used.append(name)
        logger.info("%s: %d days fetched", name, len(daily))
    except EnvironmentError:
        logger.info("%s: API key not configured – skipping", name)
    except Exception as exc:
        logger.warning("%s failed: %s", name, exc)
        errors.append(f"{name}: {exc}")


# ── Main entry point ──────────────────────────────────────────────────────────

def get_weather(lat, lon, location_name="", days=7):
    cache_key = f"{round(lat, 3)}:{round(lon, 3)}:{days}"
    if cache_key in _cache:
        return _cache[cache_key]

    named_daily, named_currents, sources_used, errors = [], [], [], []

    _try_source("open_meteo",      lambda: open_meteo.normalize(open_meteo.fetch_forecast(lat, lon, days)),          named_daily, named_currents, sources_used, errors)
    _try_source("yr_no",           lambda: yr_no.normalize(yr_no.fetch_forecast(lat, lon)),                          named_daily, named_currents, sources_used, errors)
    _try_source("weatherapi",      lambda: weatherapi_svc.normalize(weatherapi_svc.fetch_forecast(lat, lon, days)),  named_daily, named_currents, sources_used, errors)
    _try_source("tomorrow_io",     lambda: tomorrow_io.normalize(tomorrow_io.fetch_forecast(lat, lon, days)),         named_daily, named_currents, sources_used, errors)
    _try_source("openweather",     lambda: openweather.normalize(openweather.fetch_forecast(lat, lon)),               named_daily, named_currents, sources_used, errors)
    _try_source("visual_crossing", lambda: visual_crossing.normalize(visual_crossing.fetch_forecast(lat, lon, days)), named_daily, named_currents, sources_used, errors)
    _try_source("pirate_weather",  lambda: pirate_weather.normalize(pirate_weather.fetch_forecast(lat, lon)),         named_daily, named_currents, sources_used, errors)

    if not named_daily:
        raise RuntimeError(f"All weather sources failed: {'; '.join(errors)}")

    # ── Background tasks: log snapshots + fetch yesterday's actuals ──────────
    today = date.today()
    threading.Thread(
        target=forecast_logger.log_snapshots,
        args=(lat, lon, list(named_daily), today),
        daemon=True,
    ).start()
    threading.Thread(
        target=actuals_fetcher.fetch_and_store_actuals,
        args=(lat, lon),
        daemon=True,
    ).start()

    # ── Supplemental sources ─────────────────────────────────────────────────
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
        raw_climate = climate.fetch_climate_normals(lat, lon)
        climate_data = climate.normalize(raw_climate)
        sources_used.append("open_meteo_climate")
    except Exception as exc:
        logger.warning("Climate failed: %s", exc)

    # ── Load weights (cached, ~free call) ────────────────────────────────────
    weights = weight_loader.get_weights()

    result = {
        "location":        location_name,
        "latitude":        lat,
        "longitude":       lon,
        "current":         _merge_current(named_currents, weights),
        "aggregated_daily": _merge_daily(named_daily, weights),
        "air_quality":     air_data,
        "marine":          marine_data,
        "climate_normals": climate_data,
        "sources":         sources_used,
        "provider_weights": weights,
        "fetched_at":      datetime.now(timezone.utc).isoformat(),
        "errors":          errors,
    }

    _cache[cache_key] = result
    return result
