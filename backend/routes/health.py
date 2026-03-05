from flask import Blueprint, jsonify
from datetime import datetime, timezone
import services.open_meteo_climate as climate

health_bp = Blueprint("health", __name__)

@health_bp.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})

@health_bp.route("/debug/climate")
def debug_climate():
    """Test climate fetch directly — visit /api/debug/climate in browser"""
    try:
        raw = climate.fetch_climate_normals(51.5, -0.1)
        normalized = climate.normalize(raw)
        return jsonify({
            "status": "ok",
            "monthly_count": len(normalized.get("monthly_normals", [])),
            "sample": normalized.get("monthly_normals", [])[:3],
            "raw_keys": list(raw.keys()),
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "type": type(e).__name__,
        }), 500