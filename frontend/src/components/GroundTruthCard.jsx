import React, { useState } from "react";
import { useSelector } from "react-redux";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000/api";

const CONDITIONS = [
  { key: "clear",        icon: "☀️", label: "Clear"         },
  { key: "partly_cloudy",icon: "⛅", label: "Partly cloudy" },
  { key: "overcast",     icon: "☁️", label: "Overcast"      },
  { key: "rain",         icon: "🌧", label: "Rain"          },
  { key: "snow",         icon: "❄️", label: "Snow"          },
  { key: "mist",         icon: "🌫", label: "Mist"          },
  { key: "storm",        icon: "⛈", label: "Storm"         },
];

function nowISO() {
  return new Date().toISOString().slice(0, 16);
}

export default function GroundTruthCard() {
  const location    = useSelector((s) => s.weather.location);
  const latitude    = useSelector((s) => s.weather.latitude);
  const longitude   = useSelector((s) => s.weather.longitude);

  const [conditions,   setConditions]   = useState(null);
  const [temperature,  setTemperature]  = useState("");
  const [timestamp,    setTimestamp]    = useState(nowISO());
  const [notes,        setNotes]        = useState("");
  const [name,         setName]         = useState("");
  const [status,       setStatus]       = useState("idle"); // idle|submitting|success|error
  const [expanded,     setExpanded]     = useState(false);

  async function submit() {
    if (!conditions) return;
    setStatus("submitting");
    try {
      const body = {
        conditions,
        submitted_at:   new Date(timestamp).toISOString(),
        location_name:  location || null,
        lat:            latitude  || null,
        lon:            longitude || null,
        temperature_c:  temperature !== "" ? parseFloat(temperature) : null,
        notes:          notes.trim() || null,
        contributor_name: name.trim() || null,
      };
      const resp = await fetch(`${API_BASE}/ground-truth`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(body),
      });
      if (!resp.ok) throw new Error();
      setStatus("success");
      setTimeout(() => {
        setStatus("idle");
        setConditions(null);
        setTemperature("");
        setNotes("");
        setTimestamp(nowISO());
      }, 2500);
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  }

  return (
    <div className="rounded-3xl border border-teal-500/15 bg-teal-500/5 backdrop-blur-sm">
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between p-5 text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-xl">📡</span>
          <div>
            <div className="text-sm font-semibold text-teal-300">
              Submit a ground reading
            </div>
            <div className="text-xs text-slate-500 mt-0.5">
              Help calibrate model weights
            </div>
          </div>
        </div>
        <span className="text-slate-500 text-sm">{expanded ? "▲" : "▼"}</span>
      </button>

      {/* Expandable form */}
      {expanded && (
        <div className="px-5 pb-5 space-y-4">
          {status === "success" ? (
            <div className="text-center py-4 space-y-1">
              <div className="text-3xl">✅</div>
              <p className="text-teal-400 font-semibold text-sm">Reading submitted — thank you</p>
            </div>
          ) : (
            <>
              {/* Conditions — required */}
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
                  Conditions <span className="text-red-400">*</span>
                </p>
                <div className="flex flex-wrap gap-2">
                  {CONDITIONS.map((c) => (
                    <button
                      key={c.key}
                      onClick={() => setConditions(c.key)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full
                                  text-xs font-medium border transition-all
                                  ${conditions === c.key
                                    ? "bg-teal-500/20 border-teal-400/50 text-teal-300"
                                    : "bg-white/5 border-white/10 text-slate-400 hover:border-white/20"
                                  }`}
                    >
                      <span>{c.icon}</span>
                      <span>{c.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Temperature — optional */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-1.5">
                    Temperature (°C)
                  </p>
                  <input
                    type="number"
                    value={temperature}
                    onChange={(e) => setTemperature(e.target.value)}
                    placeholder="e.g. 4"
                    className="w-full bg-white/5 border border-white/10 rounded-xl
                               px-3 py-2 text-sm text-white placeholder-slate-600
                               focus:outline-none focus:border-teal-500/40"
                  />
                </div>

                {/* Timestamp — defaults to now, editable */}
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-1.5">
                    When
                  </p>
                  <input
                    type="datetime-local"
                    value={timestamp}
                    onChange={(e) => setTimestamp(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl
                               px-3 py-2 text-sm text-white
                               focus:outline-none focus:border-teal-500/40"
                  />
                </div>
              </div>

              {/* Optional extras */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-1.5">
                    Your name (optional)
                  </p>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Anonymous"
                    maxLength={60}
                    className="w-full bg-white/5 border border-white/10 rounded-xl
                               px-3 py-2 text-sm text-white placeholder-slate-600
                               focus:outline-none focus:border-teal-500/40"
                  />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-1.5">
                    Notes (optional)
                  </p>
                  <input
                    type="text"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="e.g. icy above 800m"
                    maxLength={280}
                    className="w-full bg-white/5 border border-white/10 rounded-xl
                               px-3 py-2 text-sm text-white placeholder-slate-600
                               focus:outline-none focus:border-teal-500/40"
                  />
                </div>
              </div>

              {status === "error" && (
                <p className="text-red-400 text-xs">Submission failed — please try again.</p>
              )}

              <button
                onClick={submit}
                disabled={!conditions || status === "submitting"}
                className="w-full py-2.5 rounded-2xl text-sm font-semibold
                           bg-teal-500/15 border border-teal-500/30 text-teal-300
                           disabled:opacity-40 disabled:cursor-not-allowed
                           hover:bg-teal-500/25 transition-all"
              >
                {status === "submitting" ? "Submitting…" : "Submit reading ↗"}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}