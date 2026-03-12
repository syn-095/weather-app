from flask import Blueprint, request, jsonify
import os
from datetime import datetime, timezone
from services.supabase_client import get_client

analytics_bp = Blueprint("analytics", __name__)

BOT_AGENTS = ("bot", "crawler", "spider", "python-requests", "curl", "wget",
              "scrapy", "httpclient", "go-http", "java/", "axios")


def _is_bot(req):
    ua = (req.headers.get("User-Agent") or "").lower()
    return any(b in ua for b in BOT_AGENTS)


@analytics_bp.route("/analytics/pageview", methods=["POST"])
def pageview():
    if _is_bot(request):
        return jsonify({"ok": False, "reason": "bot"}), 200

    data     = request.get_json(silent=True) or {}
    location = data.get("location", "")
    now      = datetime.now(timezone.utc)

    try:
        get_client().table("analytics").insert({
            "date":     now.strftime("%Y-%m-%d"),
            "hour":     now.hour,
            "location": location or None,
        }).execute()
    except Exception as e:
        # Never let analytics errors affect the user
        print(f"[analytics] write error: {e}")

    return jsonify({"ok": True}), 200


@analytics_bp.route("/analytics/summary", methods=["GET"])
def summary():
    secret = request.args.get("secret") or request.cookies.get("admin_secret", "")
    if secret != os.getenv("FEEDBACK_ADMIN_SECRET", ""):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        result = get_client().table("analytics") \
            .select("date,hour,location") \
            .execute()
        return jsonify({"ok": True, "count": len(result.data or [])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500