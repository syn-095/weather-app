import threading
from flask import Blueprint, request, jsonify
from services.supabase_client import get_client
from datetime import datetime, timezone

gt_bp = Blueprint("ground_truth", __name__)

VALID_CONDITIONS = [
    "clear", "partly_cloudy", "overcast",
    "rain", "snow", "mist", "storm"
]


@gt_bp.route("/ground-truth", methods=["POST"])
def submit():
    body = request.get_json(silent=True) or {}

    conditions = body.get("conditions", "").strip()
    if conditions not in VALID_CONDITIONS:
        return jsonify({"error": f"conditions must be one of {VALID_CONDITIONS}"}), 400

    # Timestamp: use provided or default to now
    submitted_at = body.get("submitted_at")
    if submitted_at:
        try:
            datetime.fromisoformat(submitted_at)
        except ValueError:
            return jsonify({"error": "invalid submitted_at format, use ISO 8601"}), 400
    else:
        submitted_at = datetime.now(timezone.utc).isoformat()

    temp = body.get("temperature_c")
    if temp is not None:
        try:
            temp = float(temp)
        except (ValueError, TypeError):
            return jsonify({"error": "temperature_c must be a number"}), 400

    entry = {
        "submitted_at":      submitted_at,
        "location_name":     body.get("location_name", "").strip() or None,
        "lat":               body.get("lat"),
        "lon":               body.get("lon"),
        "conditions":        conditions,
        "temperature_c":     temp,
        "notes":             (body.get("notes") or "")[:280] or None,
        "contributor_name":  (body.get("contributor_name") or "").strip() or None,
    }

    get_client().table("ground_truth").insert(entry).execute()

    # Lift this reading into actuals and recalculate weights in the background.
    # fetch_and_store_actuals handles the lift + recalc pipeline.
    # If no lat/lon was provided we fall back to a direct weight recalc.
    import services.actuals_fetcher as actuals_fetcher
    import services.weight_calculator as weight_calculator
    lat = entry.get("lat")
    lon = entry.get("lon")
    if lat is not None and lon is not None:
        threading.Thread(
            target=actuals_fetcher.fetch_and_store_actuals,
            args=(lat, lon),
            daemon=True,
        ).start()
    else:
        threading.Thread(target=weight_calculator.calculate_weights, daemon=True).start()

    return jsonify({"status": "ok"}), 201


@gt_bp.route("/ground-truth", methods=["GET"])
def get_readings():
    import os
    secret = request.args.get("secret", "")
    if secret != os.getenv("FEEDBACK_ADMIN_SECRET", ""):
        return jsonify({"error": "Unauthorized"}), 401

    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius_km = request.args.get("radius_km", 50, type=float)

    query = get_client().table("ground_truth") \
        .select("*") \
        .order("submitted_at", desc=True) \
        .limit(200)

    result = query.execute()
    data = result.data or []

    # Filter by radius if lat/lon provided
    if lat and lon:
        import math
        def dist(r):
            if not r.get("lat") or not r.get("lon"):
                return 999
            dlat = math.radians(r["lat"] - lat)
            dlon = math.radians(r["lon"] - lon)
            a = math.sin(dlat/2)**2 + \
                math.cos(math.radians(lat)) * \
                math.cos(math.radians(r["lat"])) * \
                math.sin(dlon/2)**2
            return 6371 * 2 * math.asin(math.sqrt(a))
        data = [r for r in data if dist(r) <= radius_km]

    return jsonify({"count": len(data), "readings": data})