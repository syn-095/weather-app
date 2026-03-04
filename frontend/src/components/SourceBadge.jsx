import React from "react";

const SOURCE_META = {
  open_meteo: { label: "Open-Meteo", color: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
  weatherapi: { label: "WeatherAPI", color: "bg-violet-500/15 text-violet-300 border-violet-500/30" },
  aggregated: { label: "Aggregated", color: "bg-sky-500/15 text-sky-300 border-sky-500/30" },
};

export default function SourceBadge({ source }) {
  const meta = SOURCE_META[source] || {
    label: source,
    color: "bg-white/10 text-slate-300 border-white/20",
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${meta.color}`}>
      {meta.label}
    </span>
  );
}