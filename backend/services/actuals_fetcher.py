"""
actuals_fetcher.py
Fetches yesterday's observed weather from Open-Meteo (using past_days=2 on the
standard forecast endpoint — NWP analysis, available immediately) and stores it
in the `actuals` Supabase table.  Also lifts any user-submitted ground truth
readings for the same location into the actuals table so they feed the weight
calculator.

Called in a background thread from aggregator.get_weather() — never blocks responses.
"""

import logging
import math
import requests
from datetime import date, datetime, timedelta, timezone
from services.supabase_client import get_client
from services import weight_calculator

logger = logging.getLogger(__name__)

_OM_URL = "https://api.open-meteo.com/v1/forecast"

# WMO code → coarse condition bin (same mapping as forecast_logger)
def _conditions_bin(code: int) -> str:
    if code in (0, 1):             return "clear"
    if code in (2, 3, 45, 48):    return "cloudy"
    if code in (51, 53, 55, 61, 63, 80, 81): return "precip_light"
    if code in (65, 82):           return "precip_heavy"
    if code in (71, 73, 75, 77, 85, 86):     return "snow"
    if code in (95, 96, 99):       return "storm"
    return "cloudy"


def _round_coord(v: float) -> float:
    return round(v, 4)


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _ground_truth_to_conditions(gt_conditions: str) -> str:
    """Map user-submitted condition string to our 5-bin system."""
    mapping = {
        "clear":        "clear",
        "partly_cloudy":"cloudy",
        "overcast":     "cloudy",
        "mist":         "cloudy",
        "rain":         "precip_light",
        "storm":        "storm",
        "snow":         "snow",
    }
    return mapping.get(gt_conditions, "cloudy")


def fetch_and_store_actuals(lat: float, lon: float):
    """
    Main entry point called from the aggregator background thread.
    1. Fetches yesterday's actuals from Open-Meteo and upserts into `actuals`.
    2. Converts nearby user ground truth readings into actuals rows.
    3. Triggers weight recalculation if new data was stored.
    """
    lat_r = _round_coord(lat)
    lon_r = _round_coord(lon)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    stored_new = False

    stored_new |= _fetch_om_actuals(lat_r, lon_r, yesterday)
    stored_new |= _lift_ground_truth(lat_r, lon_r, yesterday)

    if stored_new:
        try:
            weight_calculator.calculate_weights()
        except Exception as exc:
            logger.warning("actuals_fetcher: weight recalc failed: %s", exc)


def _fetch_om_actuals(lat_r: float, lon_r: float, yesterday: str) -> bool:
    """Fetch Open-Meteo historical analysis for yesterday. Returns True if inserted."""
    client = get_client()

    # Check if we already have this entry
    try:
        existing = client.table("actuals") \
            .select("id") \
            .eq("lat", lat_r) \
            .eq("lon", lon_r) \
            .eq("date", yesterday) \
            .eq("source", "open_meteo_historical") \
            .execute()
        if existing.data:
            return False
    except Exception as exc:
        logger.warning("actuals_fetcher: existence check failed: %s", exc)
        return False

    try:
        resp = requests.get(_OM_URL, params={
            "latitude":       lat_r,
            "longitude":      lon_r,
            "past_days":      2,
            "forecast_days":  0,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "wind_speed_10m_max",
                "weathercode",
            ],
            "timezone":       "UTC",
            "wind_speed_unit":"kmh",
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("actuals_fetcher: Open-Meteo request failed: %s", exc)
        return False

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    try:
        idx = dates.index(yesterday)
    except ValueError:
        logger.warning("actuals_fetcher: yesterday (%s) not in Open-Meteo response", yesterday)
        return False

    def _safe(lst, i, cast=float):
        try:
            v = lst[i]
            return cast(v) if v is not None else None
        except (IndexError, TypeError, ValueError):
            return None

    t_max   = _safe(daily.get("temperature_2m_max", []), idx)
    t_min   = _safe(daily.get("temperature_2m_min", []), idx)
    precip  = _safe(daily.get("precipitation_sum", []), idx)
    wind    = _safe(daily.get("wind_speed_10m_max", []), idx)
    wcode   = _safe(daily.get("weathercode", []), idx, int)
    t_avg   = round((t_max + t_min) / 2, 1) if t_max is not None and t_min is not None else None
    cond    = _conditions_bin(wcode) if wcode is not None else None

    row = {
        "lat":            lat_r,
        "lon":            lon_r,
        "date":           yesterday,
        "source":         "open_meteo_historical",
        "temp_max_c":     round(t_max, 2) if t_max is not None else None,
        "temp_min_c":     round(t_min, 2) if t_min is not None else None,
        "temp_avg_c":     t_avg,
        "precipitation_mm": round(precip, 2) if precip is not None else None,
        "wind_max_kmh":   round(wind, 1) if wind is not None else None,
        "conditions":     cond,
    }

    try:
        client.table("actuals").insert(row).execute()
        logger.info("actuals_fetcher: stored OM historical for %s/%s on %s", lat_r, lon_r, yesterday)
        return True
    except Exception as exc:
        logger.warning("actuals_fetcher: actuals insert failed: %s", exc)
        return False


def _lift_ground_truth(lat_r: float, lon_r: float, yesterday: str) -> bool:
    """
    Promote nearby user ground truth readings from `yesterday` into the `actuals`
    table (source='user_ground_truth') if not already present.
    Returns True if a new row was inserted.
    """
    client = get_client()

    # Already have user GT for this location/date?
    try:
        existing = client.table("actuals") \
            .select("id") \
            .eq("lat", lat_r) \
            .eq("lon", lon_r) \
            .eq("date", yesterday) \
            .eq("source", "user_ground_truth") \
            .execute()
        if existing.data:
            return False
    except Exception:
        return False

    # Fetch recent ground truth readings for yesterday
    try:
        gt_resp = client.table("ground_truth") \
            .select("lat,lon,temperature_c,conditions,submitted_at") \
            .execute()
        readings = gt_resp.data or []
    except Exception as exc:
        logger.warning("actuals_fetcher: ground_truth fetch failed: %s", exc)
        return False

    # Filter: within 50 km of query location and submitted on yesterday
    nearby = []
    for r in readings:
        r_lat = r.get("lat")
        r_lon = r.get("lon")
        submitted = (r.get("submitted_at") or "")[:10]
        if submitted != yesterday:
            continue
        if r_lat is None or r_lon is None:
            continue
        if _haversine_km(lat_r, lon_r, r_lat, r_lon) > 50:
            continue
        nearby.append(r)

    if not nearby:
        return False

    # Aggregate: average temperature, majority-vote conditions
    temps = [r["temperature_c"] for r in nearby if r.get("temperature_c") is not None]
    avg_temp = round(sum(temps) / len(temps), 1) if temps else None

    from collections import Counter
    cond_votes = Counter(
        _ground_truth_to_conditions(r["conditions"])
        for r in nearby if r.get("conditions")
    )
    conditions = cond_votes.most_common(1)[0][0] if cond_votes else None

    row = {
        "lat":        lat_r,
        "lon":        lon_r,
        "date":       yesterday,
        "source":     "user_ground_truth",
        "temp_avg_c": avg_temp,
        "conditions": conditions,
    }

    try:
        client.table("actuals").insert(row).execute()
        logger.info(
            "actuals_fetcher: lifted %d GT readings for %s/%s on %s",
            len(nearby), lat_r, lon_r, yesterday
        )
        return True
    except Exception as exc:
        logger.warning("actuals_fetcher: GT actuals insert failed: %s", exc)
        return False
