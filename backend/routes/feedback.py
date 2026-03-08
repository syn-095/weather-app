from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from services.supabase_client import get_client
import uuid

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.route("/feedback", methods=["POST"])
def submit_feedback():
    body    = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()

    if not message:
        return jsonify({"error": "message is required"}), 400
    if len(message) > 2000:
        return jsonify({"error": "message too long (max 2000 chars)"}), 400

    entry = {
        "id":           str(uuid.uuid4())[:8],
        "type":         body.get("type", "suggestion"),
        "message":      message,
        "location":     body.get("location"),
        "weather_data": body.get("weather_data"),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "user_agent":   request.headers.get("User-Agent", "")[:100],
        "done":         False,
    }

    get_client().table("feedback").insert(entry).execute()
    return jsonify({"status": "ok", "id": entry["id"]}), 201


@feedback_bp.route("/feedback", methods=["GET"])
def get_feedback():
    import os
    secret = request.args.get("secret", "")
    if secret != os.getenv("FEEDBACK_ADMIN_SECRET", ""):
        return jsonify({"error": "Unauthorized"}), 401

    result = get_client().table("feedback") \
        .select("*") \
        .order("submitted_at", desc=True) \
        .execute()

    data = result.data or []
    filter_type = request.args.get("type")
    if filter_type:
        data = [f for f in data if f.get("type") == filter_type]

    return jsonify({"count": len(data), "feedback": data})