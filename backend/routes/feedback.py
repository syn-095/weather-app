from flask import Blueprint, jsonify, request
from datetime import datetime, timezone
import json, os, uuid

feedback_bp = Blueprint("feedback", __name__)
FEEDBACK_FILE = "/tmp/feedback.json"


def _load():
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def _save(data):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(data, f, indent=2)


@feedback_bp.route("/feedback", methods=["POST"])
def submit_feedback():
    body = request.get_json(silent=True) or {}

    feedback_type = body.get("type", "suggestion")  # "suggestion" | "ground_truth"
    message       = (body.get("message") or "").strip()
    location      = body.get("location")             # for ground truth later
    weather_data  = body.get("weather_data")         # for ground truth later

    if not message:
        return jsonify({"error": "message is required"}), 400
    if len(message) > 2000:
        return jsonify({"error": "message too long (max 2000 chars)"}), 400

    entry = {
        "id":           str(uuid.uuid4())[:8],
        "type":         feedback_type,
        "message":      message,
        "location":     location,
        "weather_data": weather_data,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "user_agent":   request.headers.get("User-Agent", "")[:100],
    }

    all_feedback = _load()
    all_feedback.append(entry)
    _save(all_feedback)

    return jsonify({"status": "ok", "id": entry["id"]}), 201


@feedback_bp.route("/feedback", methods=["GET"])
def get_feedback():
    """Simple admin view — list all feedback"""
    secret = request.args.get("secret", "")
    admin_secret = os.getenv("FEEDBACK_ADMIN_SECRET", "")

    if not admin_secret or secret != admin_secret:
        return jsonify({"error": "Unauthorized"}), 401

    all_feedback = _load()
    feedback_type = request.args.get("type")
    if feedback_type:
        all_feedback = [f for f in all_feedback if f.get("type") == feedback_type]

    return jsonify({
        "count": len(all_feedback),
        "feedback": sorted(all_feedback, key=lambda x: x["submitted_at"], reverse=True),
    })