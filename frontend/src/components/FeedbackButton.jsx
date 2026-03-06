import React, { useState } from "react";
import { useSelector } from "react-redux";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000/api";

export default function FeedbackButton() {
  const [open, setOpen]       = useState(false);
  const [message, setMessage] = useState("");
  const [status, setStatus]   = useState("idle"); // idle | submitting | success | error
  const location = useSelector((s) => s.weather.location);

  async function submit() {
    if (!message.trim()) return;
    setStatus("submitting");
    try {
      const resp = await fetch(`${API_BASE}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: "suggestion",
          message: message.trim(),
          location: location || null,
        }),
      });
      if (!resp.ok) throw new Error("Failed");
      setStatus("success");
      setMessage("");
      setTimeout(() => { setOpen(false); setStatus("idle"); }, 2000);
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2
                   px-4 py-2.5 rounded-full shadow-lg
                   bg-sky-500/20 hover:bg-sky-500/30
                   border border-sky-500/40 hover:border-sky-400/60
                   text-sky-300 text-sm font-semibold
                   backdrop-blur-sm transition-all duration-200
                   hover:scale-105 active:scale-95"
      >
        <span>💬</span>
        <span>Feedback</span>
      </button>

      {/* Modal */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
             onClick={(e) => e.target === e.currentTarget && setOpen(false)}>

          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setOpen(false)} />

          {/* Panel */}
          <div className="relative w-full max-w-md rounded-3xl p-6 space-y-4
                          bg-slate-900/95 border border-white/10 shadow-2xl
                          animate-in slide-in-from-bottom-4">

            {/* Header */}
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-white font-bold text-lg">Share Feedback</h2>
                <p className="text-slate-400 text-sm mt-0.5">
                  What would you like to see improved?
                </p>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-slate-500 hover:text-white transition-colors p-1"
              >
                ✕
              </button>
            </div>

            {/* Success state */}
            {status === "success" ? (
              <div className="text-center py-6 space-y-2">
                <div className="text-4xl">🎉</div>
                <p className="text-emerald-400 font-semibold">Thanks for your feedback!</p>
                <p className="text-slate-500 text-sm">We'll take a look and get back to you.</p>
              </div>
            ) : (
              <>
                {/* Text area */}
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="e.g. I'd love to see a radar map, or the UV index more prominently..."
                  maxLength={2000}
                  rows={5}
                  className="w-full rounded-2xl px-4 py-3 text-sm
                             bg-white/5 border border-white/10
                             text-white placeholder-slate-600
                             focus:outline-none focus:border-sky-500/50 focus:bg-white/8
                             resize-none transition-colors"
                />

                {/* Character count */}
                <div className="flex items-center justify-between text-xs text-slate-600">
                  <span>{message.length}/2000</span>
                  {location && (
                    <span className="text-slate-500">📍 {location}</span>
                  )}
                </div>

                {/* Error */}
                {status === "error" && (
                  <p className="text-red-400 text-xs">
                    Something went wrong — please try again.
                  </p>
                )}

                {/* Submit */}
                <button
                  onClick={submit}
                  disabled={!message.trim() || status === "submitting"}
                  className="w-full py-3 rounded-2xl font-semibold text-sm
                             bg-sky-500/25 hover:bg-sky-500/35
                             border border-sky-500/40 hover:border-sky-400/60
                             text-sky-300 disabled:opacity-40
                             disabled:cursor-not-allowed transition-all duration-200"
                >
                  {status === "submitting" ? "Sending…" : "Send Feedback"}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}