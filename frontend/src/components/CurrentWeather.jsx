import React from "react";
import { useWeather } from "../hooks/useWeather";
import WeatherIcon from "./WeatherIcon";

const SOURCE_META = {
  open_meteo:       { label: "Open-Meteo",     color: "text-emerald-400", dot: "bg-emerald-400" },
  yr_no:            { label: "Yr.no",           color: "text-orange-400",  dot: "bg-orange-400"  },
  weatherapi:       { label: "WeatherAPI",      color: "text-violet-400",  dot: "bg-violet-400"  },
  tomorrow_io:      { label: "Tomorrow.io",     color: "text-cyan-400",    dot: "bg-cyan-400"    },
  openweather:      { label: "OpenWeather",     color: "text-yellow-400",  dot: "bg-yellow-400"  },
  visual_crossing:  { label: "VisualCrossing",  color: "text-pink-400",    dot: "bg-pink-400"    },
  pirate_weather:   { label: "Pirate Weather",  color: "text-red-400",     dot: "bg-red-400"     },
  open_meteo_air:   { label: "Air Quality",     color: "text-teal-400",    dot: "bg-teal-400"    },
  open_meteo_marine:{ label: "Marine",          color: "text-blue-400",    dot: "bg-blue-400"    },
  open_meteo_climate:{ label: "Climate",        color: "text-indigo-400",  dot: "bg-indigo-400"  },
};

export default function CurrentWeather() {
  const {
    current, location, sources, fetchedAt,
    fmt, fmtWind, tUnit, wUnit, forecastStatus
  } = useWeather();

  if (forecastStatus === "loading") {
    return (
      <div className="rounded-3xl p-8 animate-pulse bg-white/5 border border-white/10">
        <div className="h-16 w-48 bg-white/10 rounded-2xl mb-4" />
        <div className="h-8 w-32 bg-white/10 rounded-xl" />
      </div>
    );
  }

  if (!current) return null;

  const lastUpdated = fetchedAt
    ? new Date(fetchedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  // Separate forecast sources from supplemental sources
  const forecastSources = sources.filter(s =>
    !s.includes("air") && !s.includes("marine") && !s.includes("climate")
  );
  const supplementalSources = sources.filter(s =>
    s.includes("air") || s.includes("marine") || s.includes("climate")
  );

  return (
    <div className="relative overflow-hidden rounded-3xl p-8
                    bg-gradient-to-br from-sky-500/20 via-blue-600/10 to-indigo-700/20
                    border border-white/15 backdrop-blur-md shadow-2xl">
      <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full
                      bg-sky-400/10 blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-wrap items-start justify-between gap-6">
        {/* Left: temp + description */}
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="text-sky-300 w-16 h-16">
              <WeatherIcon icon={current.icon} className="w-16 h-16" />
            </div>
            <div>
              <div className="text-7xl font-black text-white leading-none tracking-tighter">
                {fmt(current.temperature_c)}{tUnit}
              </div>
              <div className="text-sky-300 text-lg mt-1">{current.description}</div>
            </div>
          </div>

          <div className="text-slate-300 text-sm mt-2">
            Feels like{" "}
            <span className="text-white font-semibold">
              {current.feels_like_c != null ? `${fmt(current.feels_like_c)}${tUnit}` : "—"}
            </span>
          </div>

          {location && (
            <div className="flex items-center gap-1.5 mt-3 text-slate-300">
              <svg className="w-4 h-4 text-sky-400" fill="none" stroke="currentColor"
                   strokeWidth="2" viewBox="0 0 24 24">
                <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/>
                <circle cx="12" cy="10" r="3"/>
              </svg>
              <span className="text-base font-medium text-white">{location}</span>
            </div>
          )}
        </div>

        {/* Right: stats */}
        <div className="grid grid-cols-2 gap-3 min-w-[200px]">
          <Stat icon="💧" label="Humidity"  value={`${Math.round(current.humidity_pct)}%`} />
          <Stat icon="💨" label="Wind"      value={`${fmtWind(current.wind_speed_kmh)} ${wUnit}`} />
          <Stat icon="🌧" label="Precip"    value={`${current.precipitation_mm} mm`} />
          {current.wind_direction_deg != null && (
            <Stat icon="🧭" label="Direction" value={`${current.wind_direction_deg}°`} />
          )}
          {current.uv_index != null && (
            <Stat icon="☀️" label="UV Index" value={`${current.uv_index?.toFixed(1)}`} />
          )}
        </div>
      </div>

      {/* Sources section */}
      <div className="relative z-10 mt-5 pt-4 border-t border-white/10 space-y-3">

        {/* Forecast sources — shown as coloured pills */}
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
            Forecast sources ({forecastSources.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {forecastSources.length === 0 && (
              <span className="text-slate-600 text-xs">None active</span>
            )}
            {forecastSources.map((src) => {
              const meta = SOURCE_META[src] || { label: src, color: "text-slate-300", dot: "bg-slate-400" };
              return (
                <span
                  key={src}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-full
                             bg-white/5 border border-white/10 text-xs font-medium"
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${meta.dot} flex-shrink-0`} />
                  <span className={meta.color}>{meta.label}</span>
                </span>
              );
            })}
          </div>
        </div>

        {/* Supplemental sources */}
        {supplementalSources.length > 0 && (
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
              Supplemental data
            </p>
            <div className="flex flex-wrap gap-2">
              {supplementalSources.map((src) => {
                const meta = SOURCE_META[src] || { label: src, color: "text-slate-300", dot: "bg-slate-400" };
                return (
                  <span
                    key={src}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded-full
                               bg-white/5 border border-white/10 text-xs font-medium"
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${meta.dot} flex-shrink-0`} />
                    <span className={meta.color}>{meta.label}</span>
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Timestamp */}
        <div className="flex justify-end">
          {lastUpdated && (
            <span className="text-xs text-slate-600">Updated {lastUpdated}</span>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ icon, label, value }) {
  return (
    <div className="bg-white/5 rounded-2xl px-3 py-2.5 border border-white/10">
      <div className="text-lg leading-none mb-1">{icon}</div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="text-sm font-semibold text-white">{value}</div>
    </div>
  );
}