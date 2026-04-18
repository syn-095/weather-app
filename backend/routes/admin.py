from flask import Blueprint, request, make_response, redirect
import os
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from services.supabase_client import get_client
import services.weight_calculator as weight_calculator

admin_bp = Blueprint("admin", __name__)


def _check_auth(req):
    secret = req.args.get("secret") or req.cookies.get("admin_secret", "")
    return secret == os.getenv("FEEDBACK_ADMIN_SECRET", ""), secret


def _load_analytics():
    """Load analytics from Supabase — persists across redeploys."""
    try:
        result = get_client().table("analytics") \
            .select("date,hour,location") \
            .order("created_at", desc=False) \
            .execute()
        return result.data or []
    except Exception:
        return []


def _nav(secret, active):
    tabs = [("feedback", "💬 Feedback"), ("analytics", "📊 Analytics"),
            ("ground-truth", "🏔 Ground Truth"), ("weights", "⚖️ Weights")]
    html = '<div style="display:flex;gap:8px;margin-bottom:28px;flex-wrap:wrap">'
    for key, label in tabs:
        is_active = active == key
        style = (
            "background:rgba(56,189,248,0.15);color:#38bdf8;"
            "border-color:rgba(56,189,248,0.3);"
            if is_active else "color:#94a3b8;"
        )
        html += f"""<a href="/api/admin/{key}?secret={secret}"
            style="padding:8px 20px;border-radius:20px;font-size:13px;
                   text-decoration:none;border:1px solid rgba(255,255,255,0.1);
                   font-weight:600;{style}">{label}</a>"""
    html += "</div>"
    return html


def _page(secret, active, content, subtitle=""):
    nav = _nav(secret, active)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Cairn Admin</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         background:#0a0f1e;color:#e2e8f0;min-height:100vh;padding:32px 24px}}
    a{{cursor:pointer;text-decoration:none}}
    .container{{max-width:900px;margin:0 auto}}
    .stat{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
           border-radius:16px;padding:20px;text-align:center}}
    .stat-val{{font-size:32px;font-weight:800;color:white;line-height:1}}
    .stat-label{{color:#64748b;font-size:12px;margin-top:6px;
                 text-transform:uppercase;letter-spacing:.05em}}
    .bar-wrap{{background:rgba(255,255,255,0.05);border-radius:4px;height:6px;margin-top:4px}}
    .bar{{background:#38bdf8;border-radius:4px;height:6px}}
  </style>
</head>
<body>
  <div class="container">
    <div style="display:flex;justify-content:space-between;align-items:center;
                margin-bottom:24px;flex-wrap:wrap;gap:12px">
      <div>
        <h1 style="font-size:22px;font-weight:800;color:white">🏔 Cairn Admin</h1>
        {f'<p style="color:#475569;font-size:13px;margin-top:3px">{subtitle}</p>'
          if subtitle else ''}
      </div>
    </div>
    {nav}
    {content}
  </div>
</body>
</html>"""


@admin_bp.route("/admin")
@admin_bp.route("/admin/feedback")
def admin_feedback():
    authed, secret = _check_auth(request)
    if not authed:
        return _login_page()

    filter_type = request.args.get("filter", "all")

    result = get_client().table("feedback") \
        .select("*") \
        .order("submitted_at", desc=True) \
        .execute()
    all_feedback = result.data or []

    counts = {"all": 0, "suggestion": 0, "ground_truth": 0, "done": 0}
    for f in all_feedback:
        counts["all"] += 1
        t = f.get("type", "suggestion")
        if t in counts:
            counts[t] += 1
        if f.get("done"):
            counts["done"] += 1

    if filter_type == "done":
        displayed = [f for f in all_feedback if f.get("done")]
    elif filter_type == "all":
        displayed = [f for f in all_feedback if not f.get("done")]
    else:
        displayed = [f for f in all_feedback
                     if f.get("type") == filter_type and not f.get("done")]

    filter_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px">'
    for key, label in [("all","Pending"),("suggestion","Suggestions"),
                        ("ground_truth","Ground Truth"),("done","Done ✓")]:
        active = ("background:rgba(56,189,248,0.1);color:#38bdf8;"
                  "border-color:rgba(56,189,248,0.3);") if filter_type == key else ""
        filter_html += f"""<a href="/api/admin/feedback?secret={secret}&filter={key}"
            style="padding:5px 14px;border-radius:20px;font-size:12px;
                   border:1px solid rgba(255,255,255,0.1);color:#94a3b8;{active}">
            {label} <span style="color:#334155">({counts.get(key,0)})</span></a>"""
    filter_html += "</div>"

    cards = ""
    for f in displayed:
        is_done    = f.get("done", False)
        ftype      = f.get("type", "suggestion")
        type_color = "#38bdf8" if ftype == "suggestion" else "#a78bfa"
        type_label = "💡 Suggestion" if ftype == "suggestion" else "🌤 Ground Truth"
        done_style = "opacity:0.45;" if is_done else ""
        loc        = f.get("location") or ""
        loc_html   = (f'<span style="color:#64748b;font-size:11px">📍 {loc}</span>'
                      if loc else "")
        time_str   = (f.get("submitted_at") or "")[:16].replace("T", " ") + " UTC"

        cards += f"""
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
                    border-radius:16px;padding:18px;margin-bottom:10px;{done_style}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;
                      margin-bottom:10px;gap:8px;flex-wrap:wrap">
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              <span style="background:rgba(255,255,255,0.06);border-radius:20px;
                           padding:2px 10px;font-size:11px;color:{type_color}">
                {type_label}</span>
              {loc_html}
              <span style="color:#334155;font-size:11px">{time_str}</span>
            </div>
            <div style="display:flex;gap:6px;flex-shrink:0">
              <a href="/api/admin/toggle/{f['id']}?secret={secret}&filter={filter_type}"
                 style="background:{'rgba(16,185,129,0.12)' if not is_done
                        else 'rgba(100,116,139,0.1)'};
                        color:{'#34d399' if not is_done else '#64748b'};
                        border:1px solid {'rgba(16,185,129,0.25)' if not is_done
                        else 'rgba(100,116,139,0.15)'};
                        border-radius:8px;padding:4px 12px;font-size:12px;font-weight:600">
                {'✓ Done' if not is_done else '↩ Undo'}</a>
              <a href="/api/admin/delete/{f['id']}?secret={secret}&filter={filter_type}"
                 onclick="return confirm('Delete this feedback?')"
                 style="background:rgba(239,68,68,0.08);color:#f87171;
                        border:1px solid rgba(239,68,68,0.15);
                        border-radius:8px;padding:4px 12px;font-size:12px;font-weight:600">
                🗑</a>
            </div>
          </div>
          <p style="color:#cbd5e1;margin:0;line-height:1.65;font-size:14px;
                    white-space:pre-wrap">{f['message']}</p>
        </div>"""

    if not cards:
        cards = '<p style="color:#334155;text-align:center;padding:48px 0">Nothing here.</p>'

    resp = make_response(_page(
        secret, "feedback", filter_html + cards,
        f"{counts['all']} total · {counts['done']} resolved"
    ))
    resp.set_cookie("admin_secret", secret, max_age=86400*30, httponly=True)
    return resp


@admin_bp.route("/admin/ground-truth")
def admin_ground_truth():
    authed, secret = _check_auth(request)
    if not authed:
        return _login_page()

    msg = request.args.get("msg", "")

    result = get_client().table("ground_truth") \
        .select("*") \
        .order("submitted_at", desc=True) \
        .limit(100) \
        .execute()
    readings = result.data or []

    # How many are already in actuals?
    try:
        actuals_count = len(
            get_client().table("actuals")
            .select("id")
            .eq("source", "user_ground_truth")
            .execute().data or []
        )
    except Exception:
        actuals_count = "?"

    CONDITION_ICONS = {
        "clear": "☀️", "partly_cloudy": "⛅", "overcast": "☁️",
        "rain": "🌧", "snow": "❄️", "mist": "🌫", "storm": "⛈"
    }

    cards = ""
    for r in readings:
        icon     = CONDITION_ICONS.get(r.get("conditions", ""), "🌡")
        loc      = r.get("location_name") or "Unknown location"
        temp     = f"{r['temperature_c']}°C" if r.get("temperature_c") is not None else "—"
        name     = r.get("contributor_name") or "Anonymous"
        time_str = (r.get("submitted_at") or "")[:16].replace("T", " ")
        notes    = r.get("notes") or ""

        cards += f"""
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
                    border-radius:16px;padding:16px;margin-bottom:10px">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <span style="font-size:24px">{icon}</span>
            <div>
              <div style="font-size:14px;color:white;font-weight:500">{loc}</div>
              <div style="font-size:11px;color:#475569">{time_str} UTC · {name}</div>
            </div>
            <div style="margin-left:auto;font-size:20px;font-weight:700;
                        color:#38bdf8;font-family:monospace">{temp}</div>
          </div>
          {f'<p style="font-size:12px;color:#64748b;margin:0">{notes}</p>' if notes else ''}
        </div>"""

    if not cards:
        cards = '<p style="color:#334155;text-align:center;padding:48px 0">No readings yet.</p>'

    msg_html = (
        f'<p style="color:#34d399;font-size:13px;margin-bottom:16px">✓ {msg}</p>'
        if msg else ""
    )

    backfill_btn = f"""
    <div style="margin-bottom:20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap">
      <a href="/api/admin/ground-truth/backfill?secret={secret}"
         onclick="return confirm('Lift all ground truth readings into the actuals table?')"
         style="display:inline-block;padding:9px 20px;border-radius:12px;font-size:13px;
                font-weight:600;background:rgba(20,184,166,0.12);color:#2dd4bf;
                border:1px solid rgba(20,184,166,0.25);text-decoration:none">
        🔄 Backfill all readings → actuals
      </a>
      <span style="font-size:12px;color:#475569">{actuals_count} readings already in actuals table</span>
    </div>"""

    resp = make_response(_page(
        secret, "ground-truth", msg_html + backfill_btn + cards,
        f"{len(readings)} readings submitted"
    ))
    resp.set_cookie("admin_secret", secret, max_age=86400*30, httponly=True)
    return resp


@admin_bp.route("/admin/ground-truth/backfill")
def admin_ground_truth_backfill():
    authed, secret = _check_auth(request)
    if not authed:
        return "Unauthorized", 401

    import services.actuals_fetcher as actuals_fetcher
    try:
        inserted = actuals_fetcher.backfill_all_ground_truth()
        msg = f"Backfill+complete+—+{inserted}+new+actuals+row(s)+inserted"
    except Exception as exc:
        msg = f"Backfill+failed:+{exc}"

    return redirect(f"/api/admin/ground-truth?secret={secret}&msg={msg}")


@admin_bp.route("/admin/analytics")
def admin_analytics():
    authed, secret = _check_auth(request)
    if not authed:
        return _login_page()

    data = _load_analytics()
    now       = datetime.now(timezone.utc)
    today     = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    week_ago  = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    by_date     = defaultdict(int)
    by_hour     = defaultdict(int)
    by_location = defaultdict(int)
    counts = {"today": 0, "yesterday": 0, "week": 0, "month": 0, "total": len(data)}

    for e in data:
        d = e.get("date", "")
        by_date[d] += 1
        by_hour[e.get("hour", 0)] += 1
        by_location[e.get("location") or "Unknown"] += 1
        if d == today:     counts["today"] += 1
        if d == yesterday: counts["yesterday"] += 1
        if d >= week_ago:  counts["week"] += 1
        if d >= month_ago: counts["month"] += 1

    stats_html = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px">'
    for label, key, color in [
        ("Today", "today", "#38bdf8"), ("Yesterday", "yesterday", "#818cf8"),
        ("Last 7 days", "week", "#34d399"), ("Last 30 days", "month", "#fb923c"),
    ]:
        stats_html += f"""<div class="stat">
            <div class="stat-val" style="color:{color}">{counts[key]}</div>
            <div class="stat-label">{label}</div></div>"""
    stats_html += "</div>"

    last_30 = [((now - timedelta(days=i)).strftime("%Y-%m-%d"),
                by_date.get((now - timedelta(days=i)).strftime("%Y-%m-%d"), 0))
               for i in range(29, -1, -1)]
    max_v = max((v for _, v in last_30), default=1) or 1

    chart = '<div style="margin-bottom:24px">'
    chart += '<h3 style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px">Last 30 Days</h3>'
    chart += '<div style="display:flex;align-items:flex-end;gap:3px;height:80px">'
    for day, views in last_30:
        pct   = int((views / max_v) * 100)
        color = "#38bdf8" if day == today else "#1e40af"
        chart += f'<div style="flex:1;background:{color};border-radius:3px 3px 0 0;height:{max(pct,2)}%;opacity:0.8" title="{day}: {views}"></div>'
    chart += '</div></div>'

    top_locs = sorted(by_location.items(), key=lambda x: x[1], reverse=True)[:8]
    max_loc  = top_locs[0][1] if top_locs else 1
    locs = '<div><h3 style="color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px">Top Locations</h3>'
    for loc, views in top_locs:
        pct = int((views / max_loc) * 100)
        locs += f"""<div style="margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
            <span style="color:#cbd5e1">{loc}</span>
            <span style="color:#64748b">{views}</span></div>
          <div class="bar-wrap"><div class="bar" style="width:{pct}%"></div></div></div>"""
    locs += "</div>"

    content = stats_html + chart + locs if data else \
        '<p style="color:#334155;text-align:center;padding:48px 0">No visits yet.</p>'

    resp = make_response(_page(secret, "analytics", content,
                               f"{counts['total']} total visits"))
    resp.set_cookie("admin_secret", secret, max_age=86400*30, httponly=True)
    return resp


@admin_bp.route("/admin/toggle/<fid>")
def toggle_done(fid):
    authed, secret = _check_auth(request)
    if not authed:
        return "Unauthorized", 401

    current = get_client().table("feedback") \
        .select("done").eq("id", fid).execute()
    if not current.data:
        return "Not found", 404

    new_val = not current.data[0].get("done", False)
    get_client().table("feedback") \
        .update({"done": new_val}).eq("id", fid).execute()

    return redirect(
        f"/api/admin/feedback?secret={secret}"
        f"&filter={request.args.get('filter','all')}"
    )


@admin_bp.route("/admin/delete/<fid>")
def delete_feedback(fid):
    authed, secret = _check_auth(request)
    if not authed:
        return "Unauthorized", 401

    get_client().table("feedback").delete().eq("id", fid).execute()
    return redirect(
        f"/api/admin/feedback?secret={secret}"
        f"&filter={request.args.get('filter','all')}"
    )


@admin_bp.route("/admin/weights")
def admin_weights():
    authed, secret = _check_auth(request)
    if not authed:
        return _login_page()

    msg = request.args.get("msg", "")

    try:
        rows = get_client().table("provider_weights") \
            .select("*") \
            .order("provider") \
            .execute().data or []
    except Exception:
        rows = []

    # Build nested dict: provider -> metric -> row
    data = {}
    for r in rows:
        data.setdefault(r["provider"], {})[r["metric"]] = r

    METRICS = ["overall", "temperature", "precipitation", "wind", "conditions"]
    PROVIDERS = sorted(data.keys()) or [
        "open_meteo", "yr_no", "weatherapi", "tomorrow_io",
        "openweather", "visual_crossing", "pirate_weather"
    ]

    def _weight_color(w):
        if w is None: return "#475569"
        if w >= 1.15: return "#34d399"
        if w >= 1.05: return "#86efac"
        if w >= 0.95: return "#94a3b8"
        if w >= 0.85: return "#fca5a5"
        return "#f87171"

    # Header row
    header = '<tr><th style="text-align:left;padding:10px 14px;color:#64748b;font-size:11px;text-transform:uppercase">Provider</th>'
    for m in METRICS:
        header += f'<th style="padding:10px 14px;color:#64748b;font-size:11px;text-transform:uppercase;text-align:center">{m}</th>'
    header += "</tr>"

    body_rows = ""
    for provider in PROVIDERS:
        body_rows += f'<tr><td style="padding:10px 14px;color:#e2e8f0;font-size:13px;font-weight:600;white-space:nowrap">{provider}</td>'
        for metric in METRICS:
            row = data.get(provider, {}).get(metric)
            w   = row["weight"]       if row else None
            n   = row["sample_count"] if row else 0
            mae = row["mae"]          if row else None
            override = row.get("is_manual_override", False) if row else False
            low_conf = (n or 0) < 10

            color      = _weight_color(w)
            cell_style = (
                f"border:1px solid rgba(251,191,36,0.4);background:rgba(251,191,36,0.06)"
                if override else
                "border:1px solid rgba(255,255,255,0.06);background:rgba(255,255,255,0.03)"
            )
            opacity = "opacity:0.5;" if low_conf and not override else ""
            w_str   = f"{w:.2f}×" if w is not None else "—"
            mae_str = f"MAE {mae:.2f}" if mae is not None else ""
            n_str   = f"n={n}" if n else "no data"
            tip     = f"{mae_str} · {n_str}{' · manual' if override else ''}{' · low confidence' if low_conf else ''}"

            body_rows += f"""
            <td style="padding:6px;text-align:center">
              <div style="{cell_style};border-radius:10px;padding:6px 8px;{opacity}"
                   title="{tip}">
                <div style="color:{color};font-size:15px;font-weight:700;font-family:monospace">{w_str}</div>
                <div style="color:#475569;font-size:10px;margin-top:2px">{n_str}</div>
              </div>
              <form method="POST" action="/api/admin/weights/set?secret={secret}"
                    style="margin-top:4px;display:flex;gap:3px;justify-content:center">
                <input type="hidden" name="provider" value="{provider}">
                <input type="hidden" name="metric"   value="{metric}">
                <input type="number" name="weight" step="0.01" min="0.1" max="3"
                       placeholder="×"
                       style="width:48px;padding:3px 5px;border-radius:6px;font-size:11px;
                              border:1px solid rgba(255,255,255,0.1);
                              background:rgba(255,255,255,0.05);color:white;text-align:center">
                <button type="submit"
                        style="padding:3px 7px;border-radius:6px;font-size:11px;border:none;
                               background:rgba(56,189,248,0.15);color:#38bdf8;cursor:pointer">✓</button>
              </form>
            </td>"""
        body_rows += "</tr>"

    table = f"""
    <div style="overflow-x:auto;margin-bottom:24px">
      <table style="width:100%;border-collapse:separate;border-spacing:4px">
        <thead>{header}</thead>
        <tbody>{body_rows}</tbody>
      </table>
    </div>"""

    legend = """
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px;font-size:11px;color:#64748b">
      <span>🟢 ≥1.15 — well above average</span>
      <span>🟡 ≈1.0 — average</span>
      <span>🔴 ≤0.85 — below average</span>
      <span style="color:rgba(251,191,36,0.8)">🟧 amber border — manual override</span>
      <span>faded — &lt;10 samples (blending toward 1.0)</span>
    </div>"""

    recalc_btn = f"""
    <a href="/api/admin/weights/recalculate?secret={secret}"
       style="display:inline-block;padding:9px 20px;border-radius:12px;font-size:13px;
              font-weight:600;background:rgba(56,189,248,0.12);color:#38bdf8;
              border:1px solid rgba(56,189,248,0.25);text-decoration:none;margin-bottom:24px">
      🔄 Recalculate weights now
    </a>"""

    msg_html = (
        f'<p style="color:#34d399;font-size:13px;margin-bottom:16px">✓ {msg}</p>'
        if msg else ""
    )

    subtitle = f"{len(rows)} weight entries · {len(PROVIDERS)} providers"
    content  = msg_html + recalc_btn + legend + table

    resp = make_response(_page(secret, "weights", content, subtitle))
    resp.set_cookie("admin_secret", secret, max_age=86400 * 30, httponly=True)
    return resp


@admin_bp.route("/admin/weights/set", methods=["POST"])
def admin_weights_set():
    authed, secret = _check_auth(request)
    if not authed:
        return "Unauthorized", 401

    provider = request.form.get("provider", "").strip()
    metric   = request.form.get("metric",   "").strip()
    try:
        weight = float(request.form.get("weight", ""))
        weight = max(0.1, min(3.0, weight))
    except (ValueError, TypeError):
        return redirect(f"/api/admin/weights?secret={secret}&msg=Invalid+weight+value")

    if not provider or not metric:
        return redirect(f"/api/admin/weights?secret={secret}&msg=Missing+provider+or+metric")

    try:
        get_client().table("provider_weights").upsert(
            {
                "provider":           provider,
                "metric":             metric,
                "weight":             round(weight, 3),
                "is_manual_override": True,
            },
            on_conflict="provider,metric"
        ).execute()
        import services.weight_loader as weight_loader
        weight_loader.invalidate_cache()
    except Exception as exc:
        return redirect(f"/api/admin/weights?secret={secret}&msg=Error:+{exc}")

    return redirect(
        f"/api/admin/weights?secret={secret}"
        f"&msg=Set+{provider}+{metric}+to+{weight:.2f}x+(manual+override)"
    )


@admin_bp.route("/admin/weights/recalculate")
def admin_weights_recalculate():
    authed, secret = _check_auth(request)
    if not authed:
        return "Unauthorized", 401

    try:
        weight_calculator.calculate_weights()
        msg = "Weights+recalculated+successfully"
    except Exception as exc:
        msg = f"Recalculation+failed:+{exc}"

    return redirect(f"/api/admin/weights?secret={secret}&msg={msg}")


def _login_page():
    return make_response("""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Cairn Admin</title>
<style>*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#0a0f1e;
      display:flex;align-items:center;justify-content:center;min-height:100vh}
input{width:100%;padding:12px 16px;border-radius:12px;margin-bottom:10px;
       border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.05);
       color:white;font-size:15px;outline:none}
button{width:100%;padding:12px;border-radius:12px;border:none;
        background:rgba(56,189,248,0.2);color:#38bdf8;
        font-size:15px;font-weight:600;cursor:pointer}</style></head>
<body><div style="width:320px;padding:32px;background:rgba(255,255,255,0.04);
              border:1px solid rgba(255,255,255,0.08);border-radius:20px">
<h2 style="color:white;margin-bottom:20px;text-align:center">🏔 Cairn Admin</h2>
<form action="/api/admin" method="get">
<input type="password" name="secret" placeholder="Admin secret" autofocus>
<button type="submit">Login →</button></form></div></body></html>""")