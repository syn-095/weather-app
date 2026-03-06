from flask import Blueprint, request, make_response, redirect, url_for
import json, os

admin_bp = Blueprint("admin", __name__)
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


def _check_auth(req):
    secret = req.args.get("secret") or req.cookies.get("admin_secret", "")
    return secret == os.getenv("FEEDBACK_ADMIN_SECRET", ""), secret


@admin_bp.route("/admin")
def admin_dashboard():
    authed, secret = _check_auth(request)
    if not authed:
        return _login_page()

    feedback = _load()
    filter_type = request.args.get("filter", "all")
    if filter_type != "all":
        feedback = [f for f in feedback if f.get("type") == filter_type]

    done_ids = set(
        f["id"] for f in _load() if f.get("done")
    )

    counts = {"all": len(_load()), "suggestion": 0, "ground_truth": 0, "done": 0}
    for f in _load():
        t = f.get("type", "suggestion")
        if t in counts:
            counts[t] += 1
        if f.get("done"):
            counts["done"] += 1

    cards = ""
    for f in sorted(feedback, key=lambda x: x["submitted_at"], reverse=True):
        is_done = f.get("done", False)
        ftype = f.get("type", "suggestion")
        type_color = "#38bdf8" if ftype == "suggestion" else "#a78bfa"
        type_label = "💡 Suggestion" if ftype == "suggestion" else "🌤 Ground Truth"
        done_style = "opacity:0.4;text-decoration:line-through;" if is_done else ""
        loc = f.get("location") or ""
        loc_html = f'<span style="color:#94a3b8;font-size:12px">📍 {loc}</span>' if loc else ""
        time_str = f["submitted_at"][:16].replace("T", " ")

        cards += f"""
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                    border-radius:16px;padding:20px;margin-bottom:12px;{done_style}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              <span style="background:rgba(255,255,255,0.06);border-radius:20px;padding:3px 10px;
                           font-size:12px;color:{type_color}">{type_label}</span>
              {loc_html}
              <span style="color:#475569;font-size:12px">{time_str}</span>
              <span style="color:#334155;font-size:11px">#{f['id']}</span>
            </div>
            <div style="display:flex;gap:8px;flex-shrink:0">
              <a href="/api/admin/toggle/{f['id']}?secret={secret}&filter={filter_type}"
                 style="background:{'rgba(16,185,129,0.15)' if not is_done else 'rgba(100,116,139,0.15)'};
                        color:{'#34d399' if not is_done else '#64748b'};
                        border:1px solid {'rgba(16,185,129,0.3)' if not is_done else 'rgba(100,116,139,0.2)'};
                        border-radius:8px;padding:4px 12px;font-size:12px;text-decoration:none;
                        font-weight:600">
                {'✓ Done' if not is_done else '↩ Undo'}
              </a>
              <a href="/api/admin/delete/{f['id']}?secret={secret}&filter={filter_type}"
                 onclick="return confirm('Delete this feedback?')"
                 style="background:rgba(239,68,68,0.1);color:#f87171;
                        border:1px solid rgba(239,68,68,0.2);
                        border-radius:8px;padding:4px 12px;font-size:12px;text-decoration:none;
                        font-weight:600">
                🗑 Delete
              </a>
            </div>
          </div>
          <p style="color:#e2e8f0;margin:0;line-height:1.6;white-space:pre-wrap">{f['message']}</p>
        </div>
        """

    filter_tabs = ""
    for key, label in [("all", "All"), ("suggestion", "Suggestions"),
                        ("ground_truth", "Ground Truth"), ("done", "Done ✓")]:
        active = "background:rgba(56,189,248,0.15);color:#38bdf8;border-color:rgba(56,189,248,0.3);" \
                 if filter_type == key else ""
        filter_tabs += f"""
        <a href="/api/admin?secret={secret}&filter={key}"
           style="padding:6px 16px;border-radius:20px;font-size:13px;text-decoration:none;
                  border:1px solid rgba(255,255,255,0.1);color:#94a3b8;{active}">
          {label} <span style="color:#475569">({counts.get(key,0)})</span>
        </a>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>WeatherAgg — Feedback Admin</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0f1e; color: #e2e8f0; min-height: 100vh; padding: 32px 24px; }}
    a {{ cursor: pointer; }}
    .container {{ max-width: 860px; margin: 0 auto; }}
  </style>
</head>
<body>
  <div class="container">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:28px">
      <div>
        <h1 style="font-size:24px;font-weight:800;color:white">💬 Feedback Dashboard</h1>
        <p style="color:#475569;font-size:14px;margin-top:4px">WeatherAgg user submissions</p>
      </div>
      <span style="background:rgba(56,189,248,0.1);color:#38bdf8;border:1px solid rgba(56,189,248,0.2);
                   border-radius:20px;padding:6px 16px;font-size:13px;font-weight:600">
        {counts['all']} total · {counts['done']} done
      </span>
    </div>

    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:24px">
      {filter_tabs}
    </div>

    {cards if cards else '<p style="color:#475569;text-align:center;padding:40px">No feedback yet.</p>'}
  </div>
</body>
</html>"""

    resp = make_response(html)
    resp.set_cookie("admin_secret", secret, max_age=86400 * 30, httponly=True)
    return resp


@admin_bp.route("/admin/toggle/<fid>")
def toggle_done(fid):
    authed, secret = _check_auth(request)
    if not authed:
        return "Unauthorized", 401
    feedback = _load()
    for f in feedback:
        if f["id"] == fid:
            f["done"] = not f.get("done", False)
            break
    _save(feedback)
    filter_type = request.args.get("filter", "all")
    return redirect(f"/api/admin?secret={secret}&filter={filter_type}")


@admin_bp.route("/admin/delete/<fid>")
def delete_feedback(fid):
    authed, secret = _check_auth(request)
    if not authed:
        return "Unauthorized", 401
    feedback = [f for f in _load() if f["id"] != fid]
    _save(feedback)
    filter_type = request.args.get("filter", "all")
    return redirect(f"/api/admin?secret={secret}&filter={filter_type}")


def _login_page():
    return make_response("""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Admin Login</title>
  <style>
    * {{ box-sizing:border-box;margin:0;padding:0 }}
    body {{ font-family:-apple-system,sans-serif;background:#0a0f1e;
            display:flex;align-items:center;justify-content:center;min-height:100vh }}
    input {{ width:100%;padding:12px 16px;border-radius:12px;border:1px solid rgba(255,255,255,0.1);
             background:rgba(255,255,255,0.05);color:white;font-size:15px;outline:none }}
    button {{ width:100%;padding:12px;border-radius:12px;border:none;
              background:rgba(56,189,248,0.2);color:#38bdf8;font-size:15px;
              font-weight:600;cursor:pointer;margin-top:12px }}
  </style>
</head>
<body>
  <div style="width:320px;padding:32px;background:rgba(255,255,255,0.04);
              border:1px solid rgba(255,255,255,0.08);border-radius:20px">
    <h2 style="color:white;margin-bottom:20px;text-align:center">💬 Admin Login</h2>
    <form action="/api/admin" method="get">
      <input type="password" name="secret" placeholder="Enter admin secret" autofocus>
      <button type="submit">Login</button>
    </form>
  </div>
</body>
</html>""")