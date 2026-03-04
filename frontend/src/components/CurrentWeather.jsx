import React from "react";
import { useWeather } from "../hooks/useWeather";
import WeatherIcon from "./WeatherIcon";

export default function CurrentWeather() {
  const { current, location, sources, fetchedAt, fmt, fmtWind, tUnit, wUnit, forecastStatus } = useWeather();

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

  return (
    <div className="relative overflow-hidden rounded-3xl p-8
                    bg-gradient-to-br from-sky-500/20 via-blue-600/10 to-indigo-700/20
                    border border-white/15 backdrop-blur-md shadow-2xl">
      <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-sky-400/10 blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-wrap items-start justify-between gap-6">
        {/* Left: temp + feels like + location */}
        <div>
          <div className="flex items-center gap-4 mb-1">
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

          {/* Feels like — below main temp */}
          <div className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-xl
                          bg-white/5 border border-white/10">
            <span className="text-slate-400 text-sm">Feels like</span>
            <span className="text-white font-bold text-sm">
              {current.feels_like_c != null ? fmt(current.feels_like_c) : "—"}{tUnit}
            </span>
            {current.feels_like_c != null && (
              <span className="text-xs text-slate-500">
                {current.feels_like_c < current.temperature_c ? "↓ cooler" : "↑ warmer"}
              </span>
            )}
          </div>

          {/* Location */}
          {location && (
            <div className="flex items-center gap-1.5 mt-3 text-slate-300">
              <svg className="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
              <span className="text-base font-medium text-white">{location}</span>
            </div>
          )}
        </div>

        {/* Right: stats grid */}
        <div className="grid grid-cols-2 gap-3 min-w-[200px]">
          <Stat icon="💧" label="Humidity" value={`${Math.round(current.humidity_pct)}%`} />
          <Stat icon="💨" label="Wind" value={`${fmtWind(current.wind_speed_kmh)} ${wUnit}`} />
          <Stat icon="🌧" label="Precip" value={`${current.precipitation_mm} mm`} />
          {current.wind_direction_deg != null && (
            <Stat icon="🧭" label="Direction" value={`${current.wind_direction_deg}°`} />
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="relative z-10 mt-5 pt-4 border-t border-white/10 flex items-center justify-between text-xs text-slate-500">
        <span>Sources: {sources.join(" · ")}</span>
        {lastUpdated && <span>Updated {lastUpdated}</span>}
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