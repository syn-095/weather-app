from flask import Blueprint, jsonify, request
import requests
from services.aggregator import get_weather

weather_bp = Blueprint("weather", __name__)

def _validate_coords(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None, None, "lat and lon must be valid numbers"
    if not (-90 <= lat <= 90):
        return None, None, "lat must be between -90 and 90"
    if not (-180 <= lon <= 180):
        return None, None, "lon must be between -180 and 180"
    return lat, lon, None

@weather_bp.route("/forecast")
def forecast():
    lat, lon, err = _validate_coords(request.args.get("lat"), request.args.get("lon"))
    if err:
        return jsonify({"error": err}), 400
    location = request.args.get("location", f"{lat},{lon}")
    days = min(int(request.args.get("days", 7)), 14)
    try:
        data = get_weather(lat=lat, lon=lon, location_name=location, days=days)
        return jsonify(data)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        return jsonify({"error": "Internal server error", "detail": str(exc)}), 500

@weather_bp.route("/geocode")
def geocode():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter required"}), 400
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": query, "count": 5, "language": "en", "format": "json"},
            timeout=8,
        )
        resp.raise_for_status()
        results = [
            {
                "name": r.get("name"),
                "country": r.get("country"),
                "admin1": r.get("admin1"),
                "latitude": r.get("latitude"),
                "longitude": r.get("longitude"),
                "timezone": r.get("timezone"),
            }
            for r in resp.json().get("results", [])
        ]
        return jsonify({"results": results})
    except requests.RequestException as exc:
        return jsonify({"error": f"Geocoding failed: {exc}"}), 502