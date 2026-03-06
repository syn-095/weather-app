from flask import Blueprint, jsonify
from datetime import datetime, timezone
import services.open_meteo_climate as climate
import shutil, os

health_bp = Blueprint("health", __name__)

@health_bp.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})

@health_bp.route("/debug/climate")
def debug_climate():
    lat, lon = 51.5, -0.1
    try:
        if os.path.exists("/tmp/climate_cache"):
            shutil.rmtree("/tmp/climate_cache")
        raw = climate.fetch_climate_normals(lat, lon)
        normalized = climate.normalize(raw)
        return jsonify({
            "status": "ok",
            "from_cache": raw.get("_from_cache", False),
            "monthly_count": len(normalized.get("monthly_normals", [])),
            "sample": normalized.get("monthly_normals", [])[:3],
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "type": type(e).__name__}), 500

@health_bp.route("/debug/env")
def debug_env():
    import os
    secret = os.getenv("FEEDBACK_ADMIN_SECRET", "NOT_FOUND")
    return jsonify({
        "secret_length": len(secret),
        "secret_first_char": secret[0] if secret else "NOT_FOUND",
        "secret_is_42": secret == "42",
    })