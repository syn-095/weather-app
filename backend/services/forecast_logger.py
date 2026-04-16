"""
forecast_logger.py
Persists each provider's per-day forecast to the `forecast_snapshots` Supabase table
on every aggregator cache miss, so we can later compare predictions to actuals and
compute per-provider accuracy weights.

Called from aggregator.get_weather() in a background thread — never blocks responses.
"""

import logging
from datetime import date, datetime, timezone, timedelta
from services.supabase_client import get_client

logger = logging.getLogger(__name__)

# Dedup window: don't re-log the same (provider, lat, lon, date) within 6 hours.
# This covers the aggregator's TTL cache window (default 10 min) with plenty of margin.
_DEDUP_HOURS = 6


def _round_coord(v: float) -> float:
    """Round to 4 decimal places (~11 m precision) for consistent grouping."""
    return round(v, 4)


def _conditions_bin(weather_code: int) -> str:
    """Map a WMO weather code to one of 5 coarse condition bins used for scoring."""
    if weather_code in (0, 1):
        return "clear"
    if weather_code in (2, 3, 45, 48):
        return "cloudy"
    if weather_code in (51, 53, 55, 61, 63, 80, 81):
        return "precip_light"
    if weather_code in (65, 82):
        return "precip_heavy"
    if weather_code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if weather_code in (95, 96, 99):
        return "storm"
    return "cloudy"  # sensible default for unknown codes


def log_snapshots(lat: float, lon: float, provider_daily_pairs: list, today: date):
    """
    Persist forecast snapshots for every (provider, day) combination.

    Args:
        lat, lon: Query coordinates.
        provider_daily_pairs: list of (provider_name, [DailyPoint, ...]) tuples.
        today: The calendar date on which the forecast was captured.
    """
    lat_r = _round_coord(lat)
    lon_r = _round_coord(lon)
    client = get_client()

    # Fetch existing snapshots from the last _DEDUP_HOURS to avoid duplicate inserts.
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=_DEDUP_HOURS)).isoformat()
    try:
        existing_resp = client.table("forecast_snapshots") \
            .select("provider,forecast_for_date") \
            .eq("lat", lat_r) \
            .eq("lon", lon_r) \
            .execute()
        existing = {
            (r["provider"], r["forecast_for_date"])
            for r in (existing_resp.data or [])
            if r.get("captured_at", "") >= cutoff
        }
    except Exception as exc:
        logger.warning("forecast_logger: could not load existing snapshots: %s", exc)
        existing = set()

    rows = []
    for provider_name, daily_points in provider_daily_pairs:
        for dp in daily_points:
            key = (provider_name, dp.date)
            if key in existing:
                continue
            days_ahead = (
                date.fromisoformat(dp.date) - today
            ).days
            rows.append({
                "provider":           provider_name,
                "lat":                lat_r,
                "lon":                lon_r,
                "forecast_for_date":  dp.date,
                "days_ahead":         days_ahead,
                "temp_max_c":         dp.temp_max_c,
                "temp_min_c":         dp.temp_min_c,
                "temp_avg_c":         dp.temp_avg_c,
                "precipitation_mm":   dp.precipitation_mm,
                "wind_max_kmh":       dp.wind_max_kmh,
                "conditions":         _conditions_bin(dp.weather_code),
            })

    if not rows:
        return

    try:
        client.table("forecast_snapshots").insert(rows).execute()
        logger.info("forecast_logger: logged %d snapshots for %s/%s", len(rows), lat_r, lon_r)
    except Exception as exc:
        logger.warning("forecast_logger: insert failed: %s", exc)
