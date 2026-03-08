from flask import Blueprint, request, jsonify
import requests
import logging
from cachetools import TTLCache

logger = logging.getLogger(__name__)
elevation_bp = Blueprint("elevation", __name__)
_cache = TTLCache(maxsize=512, ttl=86400)


def get_elevation(lat: float, lon: float) -> float | None:
    key = f"{round(lat, 3)}:{round(lon, 3)}"
    if key in _cache:
        return _cache[key]
    try:
        # Use the standard forecast endpoint — already works on Render
        # elevation is returned in the response metadata
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  lat,
                "longitude": lon,
                "hourly":    "temperature_2m",
                "forecast_days": 1,
            },
            timeout=8
        )
        resp.raise_for_status()
        data = resp.json()
        elev = data.get("elevation")
        logger.info("Elevation for %s,%s = %s", lat, lon, elev)
        if elev is not None:
            _cache[key] = elev
        return elev
    except Exception as e:
        logger.warning("Elevation fetch failed: %s", e)
        return None


def get_prominence(lat: float, lon: float) -> float | None:
    center = get_elevation(lat, lon)
    if center is None:
        return None
    offsets = [
        (lat + 0.045, lon),
        (lat - 0.045, lon),
        (lat, lon + 0.065),
        (lat, lon - 0.065),
    ]
    surrounds = [e for la, lo in offsets
                 if (e := get_elevation(la, lo)) is not None]
    if not surrounds:
        return None
    return max(0.0, center - sum(surrounds) / len(surrounds))


@elevation_bp.route("/elevation")
def elevation():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"error": "lat and lon required"}), 400

    elev       = get_elevation(lat, lon)
    prominence = get_prominence(lat, lon)
    is_summit  = (
        (elev is not None and elev > 600) or
        (prominence is not None and prominence > 300)
    )

    return jsonify({
        "elevation_m":         elev,
        "prominence_m":        prominence,
        "suggest_summit_view": is_summit,
    })