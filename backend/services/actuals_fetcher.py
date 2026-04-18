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
    2. Converts nearby user ground truth readings (last 7 days) into actuals rows.
    3. Triggers weight recalculation if new data was stored.
    """
    lat_r = _round_coord(lat)
    lon_r = _round_coord(lon)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    stored_new = False

    stored_new |= _fetch_om_actuals(lat_r, lon_r, yesterday)
    stored_new |= _lift_ground_truth(lat_r, lon_r)

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


def _lift_ground_truth(lat_r: float, lon_r: float) -> bool:
    """
    Promote nearby user ground truth readings (last 7 days) into the `actuals`
    table (source='user_ground_truth') if not already present.
    Skips today — the day isn't over yet so conditions aren't final.
    Returns True if any new rows were inserted.
    """
    from collections import Counter
    client = get_client()

    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()

    # Fetch all GT readings and filter locally (table is small)
    try:
        gt_resp = client.table("ground_truth") \
            .select("lat,lon,temperature_c,conditions,submitted_at") \
            .execute()
        readings = gt_resp.data or []
    except Exception as exc:
        logger.warning("actuals_fetcher: ground_truth fetch failed: %s", exc)
        return False

    # Group nearby readings by date
    by_date: dict[str, list] = {}
    for r in readings:
        r_lat = r.get("lat")
        r_lon = r.get("lon")
        submitted = (r.get("submitted_at") or "")[:10]
        # Only completed past days within the last week
        if submitted < week_ago or submitted >= today:
            continue
        if r_lat is None or r_lon is None:
            continue
        if _haversine_km(lat_r, lon_r, r_lat, r_lon) > 50:
            continue
        by_date.setdefault(submitted, []).append(r)

    if not by_date:
        return False

    stored_any = False
    for day, day_readings in by_date.items():
        # Skip if already lifted for this day
        try:
            existing = client.table("actuals") \
                .select("id") \
                .eq("lat", lat_r).eq("lon", lon_r) \
                .eq("date", day).eq("source", "user_ground_truth") \
                .execute()
            if existing.data:
                continue
        except Exception:
            continue

        temps = [r["temperature_c"] for r in day_readings if r.get("temperature_c") is not None]
        avg_temp = round(sum(temps) / len(temps), 1) if temps else None

        cond_votes = Counter(
            _ground_truth_to_conditions(r["conditions"])
            for r in day_readings if r.get("conditions")
        )
        conditions = cond_votes.most_common(1)[0][0] if cond_votes else None

        try:
            client.table("actuals").insert({
                "lat":        lat_r,
                "lon":        lon_r,
                "date":       day,
                "source":     "user_ground_truth",
                "temp_avg_c": avg_temp,
                "conditions": conditions,
            }).execute()
            logger.info(
                "actuals_fetcher: lifted %d GT readings for %s/%s on %s",
                len(day_readings), lat_r, lon_r, day,
            )
            stored_any = True
        except Exception as exc:
            logger.warning("actuals_fetcher: GT actuals insert failed: %s", exc)

    return stored_any


def backfill_all_ground_truth() -> int:
    """
    Admin-triggered backfill: lift ALL historical ground truth readings into the
    `actuals` table regardless of age.  Returns count of new rows inserted.
    This rescues readings submitted before the 7-day rolling window.
    """
    from collections import Counter
    client = get_client()

    today = date.today().isoformat()

    try:
        gt_resp = client.table("ground_truth") \
            .select("lat,lon,temperature_c,conditions,submitted_at") \
            .execute()
        readings = gt_resp.data or []
    except Exception as exc:
        logger.warning("actuals_fetcher: backfill GT fetch failed: %s", exc)
        return 0

    # Group by (lat_4dp, lon_4dp, date) — skip today and readings with no location
    by_key: dict[tuple, list] = {}
    for r in readings:
        r_lat = r.get("lat")
        r_lon = r.get("lon")
        submitted = (r.get("submitted_at") or "")[:10]
        if not submitted or submitted >= today or r_lat is None or r_lon is None:
            continue
        key = (_round_coord(r_lat), _round_coord(r_lon), submitted)
        by_key.setdefault(key, []).append(r)

    inserted = 0
    for (lat_r, lon_r, day), group in by_key.items():
        try:
            existing = client.table("actuals") \
                .select("id") \
                .eq("lat", lat_r).eq("lon", lon_r) \
                .eq("date", day).eq("source", "user_ground_truth") \
                .execute()
            if existing.data:
                continue
        except Exception:
            continue

        temps = [r["temperature_c"] for r in group if r.get("temperature_c") is not None]
        avg_temp = round(sum(temps) / len(temps), 1) if temps else None

        cond_votes = Counter(
            _ground_truth_to_conditions(r["conditions"])
            for r in group if r.get("conditions")
        )
        conditions = cond_votes.most_common(1)[0][0] if cond_votes else None

        try:
            client.table("actuals").insert({
                "lat":        lat_r,
                "lon":        lon_r,
                "date":       day,
                "source":     "user_ground_truth",
                "temp_avg_c": avg_temp,
                "conditions": conditions,
            }).execute()
            inserted += 1
            logger.info("actuals_fetcher: backfilled GT for %s/%s on %s", lat_r, lon_r, day)
        except Exception as exc:
            logger.warning("actuals_fetcher: backfill insert failed: %s", exc)

    if inserted:
        try:
            weight_calculator.calculate_weights()
        except Exception as exc:
            logger.warning("actuals_fetcher: backfill weight recalc failed: %s", exc)

    return inserted
