from flask import Blueprint, jsonify
from datetime import datetime, timezone

health_bp = Blueprint("health", __name__)

@health_bp.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})