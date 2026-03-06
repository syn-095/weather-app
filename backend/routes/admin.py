from flask import Blueprint, request, make_response, redirect
import json, os
from datetime import datetime, timezone, timedelta
from collections import defaultdict

admin_bp = Blueprint("admin", __name__)
FEEDBACK_FILE  = "/tmp/feedback.json"
ANALYTICS_FILE = "/tmp/analytics.json"


def _load_feedback():
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def _save_feedback(data):
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _load_analytics():
    if not os.path.exists(ANALYTICS_FILE):
        return []
    try:
        with open(ANALYTICS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def _check_auth(req):
    secret = req.args.get("secret") or req.cookies.get("admin_secret", "")
    return secret == os.getenv("FEEDBACK_ADMIN_SECRET", ""), secret


def _nav(secret, active):
    tabs = [("feedback", "💬 Feedback"), ("analytics", "📊 Analytics")]
    html = '<div style="display:flex;gap:8px;margin-bottom:28px">'
    for key, label in tabs:
        is_active = active == key
        style = (
            "background:rgba(56,189,248,0.15);color:#38bdf8;border-color:rgba(56,189,248,0.3);"
            if is_active else "color:#94a3b8;"
        )
        html += f"""<a href="/api/admin/{key}?secret={secret}"
            style="padding:8px 20px;border-radius:20px;font-size:13px;text-decoration:none;
                   border:1px solid rgba(255,255,255,0.1);font-weight:600;{style}">{label}</a>"""
    html += "</div>"
    return html


def _page(secret, active, content, subtitle=""):
    nav = _nav(secret, active)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>WeatherAgg Admin</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         background:#0a0f1e;color:#e2e8f0;min-height:100vh;padding:32px 24px}}
    a{{cursor:pointer;text-decoration:none}}
    .container{{max-width:900px;margin:0 auto}}
    .stat{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
           border-radius:16px;padding:20px;text-align:center}}
    .stat-val{{font-size:32px;font-weight:800;color:white;line-height:1}}
    .stat-label{{color:#64748b;font-size:12px;margin-top:6px;text-transform:uppercase;letter-spacing:.05em}}
    .bar-wrap{{background:rgba(255,255,255,0.05);border-radius:4px;height:6px;margin-top:4px}}
    .bar{{background:#38bdf8;border-radius:4px;height:6px;transition:width .3s}}
  </style>
</head>
<body>
  <div class="container">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
      <div>
        <h1 style="font-size:22px;font-weight:800;color:white">WeatherAgg Admin</h1>
        {f'<p style="color:#475569;font-size:13px;margin-top:3px">{subtitle}</p>' if subtitle else ''}
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

    feedback    = _load_feedback()
    filter_type = request.args.get("filter", "all")

    counts = {"all": 0, "suggestion": 0, "ground_truth": 0, "done": 0}
    for f in feedback:
        counts["all"] += 1
        t = f.get("type", "suggestion")
        if t in counts:
            counts[t] += 1
        if f.get("done"):
            counts["done"] += 1

    displayed = feedback
    if filter_type == "done":
        displayed = [f for f in feedback if f.get("done")]
    elif filter_type != "all":
        displayed = [f for f in feedback if f.get("type") == filter_type and not f.get("done")]
    else:
        displayed = [f for f in feedback if not f.get("done")]

    # Filter tabs
    filter_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px">'
    for key, label in [("all","Pending"),("suggestion","Suggestions"),
                        ("ground_truth","Ground Truth"),("done","Done ✓")]:
        active = "background:rgba(56,189,248,0.1);color:#38bdf8;border-color:rgba(56,189,248,0.3);" \
                 if filter_type == key else ""
        filter_html += f"""<a href="/api/admin/feedback?secret={secret}&filter={key}"
            style="padding:5px 14px;border-radius:20px;font-size:12px;
                   border:1px solid rgba(255,255,255,0.1);color:#94a3b8;{active}">
            {label} <span style="color:#334155">({counts.get(key,0)})</span></a>"""
    filter_html += "</div>"

    cards = ""
    for f in sorted(displayed, key=lambda x: x["submitted_at"], reverse=True):
        is_done    = f.get("done", False)
        ftype      = f.get("type", "suggestion")
        type_color = "#38bdf8" if ftype == "suggestion" else "#a78bfa"
        type_label = "💡 Suggestion" if ftype == "suggestion" else "🌤 Ground Truth"
        done_style = "opacity:0.45;" if is_done else ""
        loc        = f.get("location") or ""
        loc_html   = f'<span style="color:#64748b;font-size:11px">📍 {loc}</span>' if loc else ""
        time_str   = f["submitted_at"][:16].replace("T", " ") + " UTC"

        cards += f"""
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
                    border-radius:16px;padding:18px;margin-bottom:10px;{done_style}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;
                      margin-bottom:10px;gap:8px;flex-wrap:wrap">
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              <span style="background:rgba(255,255,255,0.06);border-radius:20px;padding:2px 10px;
                           font-size:11px;color:{type_color}">{type_label}</span>
              {loc_html}
              <span style="color:#334155;font-size:11px">{time_str}</span>
            </div>
            <div style="display:flex;gap:6px;flex-shrink:0">
              <a href="/api/admin/toggle/{f['id']}?secret={secret}&filter={filter_type}"
                 style="background:{'rgba(16,185,129,0.12)' if not is_done else 'rgba(100,116,139,0.1)'};
                        color:{'#34d399' if not is_done else '#64748b'};
                        border:1px solid {'rgba(16,185,129,0.25)' if not is_done else 'rgba(100,116,139,0.15)'};
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
        cards = '<p style="color:#334155;text-align:center;padding:48px 0">Nothing here yet.</p>'

    content = filter_html + cards
    resp = make_response(_page(secret, "feedback", content,
                               f"{counts['all']} total · {counts['done']} resolved"))
    resp.set_cookie("admin_secret", secret, max_age=86400*30, httponly=True)
    return resp


@admin_bp.route("/admin/analytics")
def admin_analytics():
    authed, secret = _check_auth(request)
    if not authed:
        return _login_page()

    data = _load_analytics()
    now  = datetime.now(timezone.utc)
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
        loc = e.get("location") or "Unknown"
        by_location[loc] += 1
        if d == today:     counts["today"] += 1
        if d == yesterday: counts["yesterday"] += 1
        if d >= week_ago:  counts["week"] += 1
        if d >= month_ago: counts["month"] += 1

    # Stat cards
    stats_html = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px">'
    for label, key, color in [
        ("Today",      "today",     "#38bdf8"),
        ("Yesterday",  "yesterday", "#818cf8"),
        ("Last 7 days","week",      "#34d399"),
        ("Last 30 days","month",    "#fb923c"),
    ]:
        stats_html += f"""<div class="stat">
            <div class="stat-val" style="color:{color}">{counts[key]}</div>
            <div class="stat-label">{label}</div>
        </div>"""
    stats_html += "</div>"

    # 30-day bar chart
    chart_html = '<div style="margin-bottom:24px">'
    chart_html += '<h3 style="color:#94a3b8;font-size:12px;text-transform:uppercase;' \
                  'letter-spacing:.08em;margin-bottom:12px">Last 30 Days</h3>'
    chart_html += '<div style="display:flex;align-items:flex-end;gap:3px;height:80px">'

    last_30 = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        last_30.append((day, by_date.get(day, 0)))

    max_views = max((v for _, v in last_30), default=1) or 1
    for day, views in last_30:
        pct     = int((views / max_views) * 100)
        is_today = day == today
        color   = "#38bdf8" if is_today else "#1e40af"
        label   = day[5:]  # MM-DD
        chart_html += f"""<div style="flex:1;display:flex;flex-direction:column;
                               align-items:center;gap:3px;min-width:0" title="{label}: {views}">
            <div style="width:100%;background:{color};border-radius:3px 3px 0 0;
                        height:{max(pct,2)}%;opacity:{'1' if is_today else '0.7'}"></div>
        </div>"""
    chart_html += "</div>"

    # X-axis labels (every 5 days)
    chart_html += '<div style="display:flex;justify-content:space-between;' \
                  'margin-top:6px;color:#334155;font-size:10px">'
    for i, (day, _) in enumerate(last_30):
        if i % 5 == 0 or i == 29:
            chart_html += f"<span>{day[5:]}</span>"
    chart_html += "</div></div>"

    # Hourly heatmap
    hourly_html = '<div style="margin-bottom:24px">'
    hourly_html += '<h3 style="color:#94a3b8;font-size:12px;text-transform:uppercase;' \
                   'letter-spacing:.08em;margin-bottom:12px">Visits by Hour (UTC)</h3>'
    hourly_html += '<div style="display:flex;gap:3px;align-items:flex-end;height:60px">'
    max_h = max(by_hour.values(), default=1) or 1
    for h in range(24):
        v   = by_hour.get(h, 0)
        pct = int((v / max_h) * 100)
        hourly_html += f"""<div style="flex:1;display:flex;flex-direction:column;
                                align-items:center;gap:2px" title="{h:02d}:00 — {v} views">
            <div style="width:100%;background:#1d4ed8;border-radius:2px 2px 0 0;
                        height:{max(pct,3)}%;opacity:0.8"></div>
        </div>"""
    hourly_html += "</div>"
    hourly_html += '<div style="display:flex;justify-content:space-between;' \
                   'margin-top:4px;color:#334155;font-size:10px">'
    for h in [0, 6, 12, 18, 23]:
        hourly_html += f"<span>{h:02d}h</span>"
    hourly_html += "</div></div>"

    # Top locations
    top_locs = sorted(by_location.items(), key=lambda x: x[1], reverse=True)[:8]
    max_loc  = top_locs[0][1] if top_locs else 1
    locs_html = '<div><h3 style="color:#94a3b8;font-size:12px;text-transform:uppercase;' \
                'letter-spacing:.08em;margin-bottom:12px">Top Locations</h3>'
    for loc, views in top_locs:
        pct = int((views / max_loc) * 100)
        locs_html += f"""<div style="margin-bottom:10px">
            <div style="display:flex;justify-content:space-between;
                        font-size:13px;margin-bottom:4px">
              <span style="color:#cbd5e1">{loc}</span>
              <span style="color:#64748b">{views}</span>
            </div>
            <div class="bar-wrap"><div class="bar" style="width:{pct}%"></div></div>
        </div>"""
    locs_html += "</div>"

    if not data:
        content = '<p style="color:#334155;text-align:center;padding:48px 0">No visits recorded yet.</p>'
    else:
        content = stats_html + chart_html + hourly_html + locs_html

    resp = make_response(_page(secret, "analytics", content,
                               f"{counts['total']} total visits recorded"))
    resp.set_cookie("admin_secret", secret, max_age=86400*30, httponly=True)
    return resp


@admin_bp.route("/admin/toggle/<fid>")
def toggle_done(fid):
    authed, secret = _check_auth(request)
    if not authed:
        return "Unauthorized", 401
    feedback = _load_feedback()
    for f in feedback:
        if f["id"] == fid:
            f["done"] = not f.get("done", False)
            break
    _save_feedback(feedback)
    return redirect(f"/api/admin/feedback?secret={secret}&filter={request.args.get('filter','all')}")


@admin_bp.route("/admin/delete/<fid>")
def delete_feedback(fid):
    authed, secret = _check_auth(request)
    if not authed:
        return "Unauthorized", 401
    _save_feedback([f for f in _load_feedback() if f["id"] != fid])
    return redirect(f"/api/admin/feedback?secret={secret}&filter={request.args.get('filter','all')}")


def _login_page():
    return make_response("""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Admin Login</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,sans-serif;background:#0a0f1e;
          display:flex;align-items:center;justify-content:center;min-height:100vh}}
    input{{width:100%;padding:12px 16px;border-radius:12px;
           border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.05);
           color:white;font-size:15px;outline:none;margin-bottom:10px}}
    button{{width:100%;padding:12px;border-radius:12px;border:none;
            background:rgba(56,189,248,0.2);color:#38bdf8;font-size:15px;
            font-weight:600;cursor:pointer}}
  </style>
</head>
<body>
  <div style="width:320px;padding:32px;background:rgba(255,255,255,0.04);
              border:1px solid rgba(255,255,255,0.08);border-radius:20px">
    <h2 style="color:white;margin-bottom:20px;text-align:center;font-size:18px">
      🌤 WeatherAgg Admin
    </h2>
    <form action="/api/admin" method="get">
      <input type="password" name="secret" placeholder="Admin secret" autofocus>
      <button type="submit">Login →</button>
    </form>
  </div>
</body>
</html>""")