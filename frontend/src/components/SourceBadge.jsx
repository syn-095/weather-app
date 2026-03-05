import React from "react";

const SOURCE_META = {
  open_meteo:      { label: "Open-Meteo",      color: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
  weatherapi:      { label: "WeatherAPI",       color: "bg-violet-500/15 text-violet-300 border-violet-500/30"   },
  yr_no:           { label: "Yr.no",            color: "bg-orange-500/15 text-orange-300 border-orange-500/30"   },
  tomorrow_io:     { label: "Tomorrow.io",      color: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30"         },
  openweather:     { label: "OpenWeather",      color: "bg-yellow-500/15 text-yellow-300 border-yellow-500/30"   },
  visual_crossing: { label: "VisualCrossing",   color: "bg-pink-500/15 text-pink-300 border-pink-500/30"         },
  pirate_weather:  { label: "Pirate Weather",   color: "bg-red-500/15 text-red-300 border-red-500/30"            },
  aggregated:      { label: "Aggregated",       color: "bg-sky-500/15 text-sky-300 border-sky-500/30"            },
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