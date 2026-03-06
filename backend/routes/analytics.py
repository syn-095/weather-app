from flask import Blueprint, request, jsonify
import json, os, time
from datetime import datetime, timezone, timedelta
from collections import defaultdict

analytics_bp = Blueprint("analytics", __name__)
ANALYTICS_FILE = "/tmp/analytics.json"


def _load():
    if not os.path.exists(ANALYTICS_FILE):
        return []
    try:
        with open(ANALYTICS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def _save(data):
    # Keep max 10,000 entries to avoid file bloat
    if len(data) > 10000:
        data = data[-10000:]
    with open(ANALYTICS_FILE, "w") as f:
        json.dump(data, f)


@analytics_bp.route("/analytics/pageview", methods=["POST"])
def pageview():
    body = request.get_json(silent=True) or {}
    ua = request.headers.get("User-Agent", "")

    # Simple bot filter
    bot_keywords = ["bot", "crawler", "spider", "python", "curl", "wget", "scrapy"]
    if any(kw in ua.lower() for kw in bot_keywords):
        return jsonify({"status": "ignored"}), 200

    entry = {
        "ts":       time.time(),
        "date":     datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "hour":     datetime.now(timezone.utc).hour,
        "location": body.get("location", ""),
        "referrer": request.referrer or "",
        "ua":       ua[:120],
    }

    data = _load()
    data.append(entry)
    _save(data)
    return jsonify({"status": "ok"}), 201


def _summarise(data):
    now = datetime.now(timezone.utc)
    today     = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago  = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    by_date     = defaultdict(int)
    by_hour     = defaultdict(int)
    by_location = defaultdict(int)
    total = len(data)

    today_count     = 0
    yesterday_count = 0
    week_count      = 0
    month_count     = 0

    for e in data:
        d = e.get("date", "")
        by_date[d] += 1
        by_hour[str(e.get("hour", 0))] += 1
        loc = e.get("location") or "Unknown"
        by_location[loc] += 1

        if d == today:
            today_count += 1
        if d == yesterday:
            yesterday_count += 1
        if d >= week_ago:
            week_count += 1
        if d >= month_ago:
            month_count += 1

    # Last 30 days for the chart
    last_30 = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        last_30.append({"date": day, "views": by_date.get(day, 0)})

    # Hourly distribution (0-23)
    hourly = [{"hour": h, "views": by_hour.get(str(h), 0)} for h in range(24)]

    # Top locations
    top_locations = sorted(
        [{"location": k, "views": v} for k, v in by_location.items()],
        key=lambda x: x["views"], reverse=True
    )[:10]

    return {
        "total":          total,
        "today":          today_count,
        "yesterday":      yesterday_count,
        "last_7_days":    week_count,
        "last_30_days":   month_count,
        "last_30_chart":  last_30,
        "hourly":         hourly,
        "top_locations":  top_locations,
    }


@analytics_bp.route("/analytics/summary")
def summary():
    import os as _os
    secret = request.args.get("secret", "")
    if secret != _os.getenv("FEEDBACK_ADMIN_SECRET", ""):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(_summarise(_load()))