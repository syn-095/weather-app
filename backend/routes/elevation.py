from flask import Blueprint, request, jsonify
import requests
from cachetools import TTLCache

elevation_bp = Blueprint("elevation", __name__)
_cache = TTLCache(maxsize=512, ttl=86400)  # 24hr — elevation doesn't change


def get_elevation(lat: float, lon: float) -> float | None:
    key = f"{round(lat, 3)}:{round(lon, 3)}"
    if key in _cache:
        return _cache[key]
    try:
        resp = requests.get(
            "https://api.open-topo-data.com/v1/srtm30m",
            params={"locations": f"{lat},{lon}"},
            timeout=5
        )
        resp.raise_for_status()
        elev = resp.json()["results"][0]["elevation"]
        _cache[key] = elev
        return elev
    except Exception:
        return None


def get_prominence(lat: float, lon: float) -> float | None:
    """
    Estimate local prominence by comparing point elevation
    to average of surrounding points at ~5km offset.
    Rough but free and API-key-free.
    """
    center = get_elevation(lat, lon)
    if center is None:
        return None
    offsets = [
        (lat + 0.045, lon),
        (lat - 0.045, lon),
        (lat, lon + 0.065),
        (lat, lon - 0.065),
    ]
    surrounds = []
    for la, lo in offsets:
        e = get_elevation(la, lo)
        if e is not None:
            surrounds.append(e)
    if not surrounds:
        return None
    avg_surround = sum(surrounds) / len(surrounds)
    return max(0.0, center - avg_surround)


@elevation_bp.route("/elevation")
def elevation():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"error": "lat and lon required"}), 400

    elev = get_elevation(lat, lon)
    prominence = get_prominence(lat, lon)

    # Summit view threshold: elevation > 600m OR prominence > 300m
    # This catches low-but-serious Scottish hills and high Alpine peaks alike
    is_summit = (
        (elev is not None and elev > 600) or
        (prominence is not None and prominence > 300)
    )

    return jsonify({
        "elevation_m":   elev,
        "prominence_m":  prominence,
        "suggest_summit_view": is_summit,
    })