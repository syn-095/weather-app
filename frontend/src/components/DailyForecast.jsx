import React from "react";
import { useWeather } from "../hooks/useWeather";
import WeatherIcon from "./WeatherIcon";

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function dayLabel(dateStr) {
  const d = new Date(dateStr + "T12:00:00");
  const today = new Date();
  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === new Date(today.getTime() + 86400000).toDateString()) return "Tomorrow";
  return DAY_NAMES[d.getDay()];
}

const SOURCE_COLOURS = {
  open_meteo: "bg-emerald-400",
  weatherapi:  "bg-violet-400",
  yr_no:       "bg-orange-400",
  aggregated:  "bg-sky-400",
};

export default function DailyForecast() {
  const { aggregatedDaily, selectedDayIndex, selectDay, fmt, tUnit, forecastStatus } = useWeather();

  if (forecastStatus === "loading") {
    return (
      <div className="flex gap-3 overflow-x-auto pb-2">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="flex-shrink-0 w-28 h-56 rounded-2xl bg-white/5 animate-pulse border border-white/10" />
        ))}
      </div>
    );
  }

  if (!aggregatedDaily.length) return null;

  const allMax = aggregatedDaily.map((d) => d.temp_max_c);
  const allMin = aggregatedDaily.map((d) => d.temp_min_c);
  const globalMax = Math.max(...allMax);
  const globalMin = Math.min(...allMin);
  const range = globalMax - globalMin || 1;

  const weekAvg =
    aggregatedDaily.reduce(
      (s, d) => s + (d.temp_avg_c ?? (d.temp_max_c + d.temp_min_c) / 2), 0
    ) / aggregatedDaily.length;

  return (
    <div className="space-y-3">
      {/* Legend */}
      <div className="flex items-center gap-3 text-xs text-slate-500 px-1 flex-wrap">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
          Day avg
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
          Open-Meteo
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-orange-400 inline-block" />
          Yr.no
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-violet-400 inline-block" />
          WeatherAPI
        </span>
      </div>

      {/* Day cards */}
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
        {aggregatedDaily.map((day, i) => {
          const isSelected = i === selectedDayIndex;
          const avgTemp = day.temp_avg_c ?? (day.temp_max_c + day.temp_min_c) / 2;

          const barTop    = ((globalMax - day.temp_max_c) / range) * 100;
          const barHeight = ((day.temp_max_c - day.temp_min_c) / range) * 100;
          const avgDotPct = ((globalMax - avgTemp) / range) * 100;

          // Only use hourly entries that have a real feels_like_c value
          // (Yr.no doesn't supply it, so filter those out)
          const hourlyWithFeels = (day.hourly || []).filter(
            (h) => h.feels_like_c != null && h.feels_like_c !== 0
          );
          const avgFeelsLike = hourlyWithFeels.length
            ? hourlyWithFeels.reduce((s, h) => s + h.feels_like_c, 0) /
              hourlyWithFeels.length
            : null;

          const hourlyWithProb = (day.hourly || []).filter(
            (h) => h.precipitation_probability != null
          );
          const avgPrecipProb = hourlyWithProb.length
            ? Math.round(
                hourlyWithProb.reduce((s, h) => s + h.precipitation_probability, 0) /
                hourlyWithProb.length
              )
            : null;

          const daySources = day.sources || [];

          return (
            <button
              key={day.date}
              onClick={() => selectDay(i)}
              className={`flex-shrink-0 w-28 rounded-2xl p-3 border transition-all duration-200 text-center
                flex flex-col items-center gap-1.5
                ${isSelected
                  ? "bg-sky-500/25 border-sky-400/50 shadow-lg shadow-sky-500/10"
                  : "bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20"
                }`}
            >
              {/* Day name */}
              <span className={`text-xs font-bold uppercase tracking-wider
                ${isSelected ? "text-sky-300" : "text-slate-400"}`}>
                {dayLabel(day.date)}
              </span>

              {/* Icon */}
              <div className={`${isSelected ? "text-sky-300" : "text-slate-400"} w-8 h-8`}>
                <WeatherIcon icon={day.icon} className="w-8 h-8" />
              </div>

              {/* Range bar */}
              <div className="relative w-2 h-16 bg-white/10 rounded-full mx-auto my-1">
                <div
                  className={`absolute w-full rounded-full transition-all duration-300
                    ${isSelected ? "bg-sky-400/60" : "bg-slate-500/60"}`}
                  style={{ top: `${barTop}%`, height: `${Math.max(barHeight, 8)}%` }}
                />
                <div
                  className="absolute left-1/2 -translate-x-1/2 w-3 h-3 rounded-full
                             bg-red-400 border-2 border-slate-900 shadow-md z-10"
                  style={{ top: `calc(${avgDotPct}% - 6px)` }}
                />
              </div>

              {/* Avg temp — large, centred, white */}
              <div className="text-white text-sm font-bold">
                {fmt(avgTemp)}{tUnit}
              </div>

              {/* Min / Max on separate row, smaller */}
              <div className="w-full flex items-center justify-between px-1">
                <span className="text-blue-400 text-xs font-medium">
                  ↓{fmt(day.temp_min_c)}
                </span>
                <span className="text-red-400 text-xs font-medium">
                  ↑{fmt(day.temp_max_c)}
                </span>
              </div>

              {/* Feels like */}
              {avgFeelsLike != null && (
                <div className="text-slate-400 text-xs">
                  FL {fmt(avgFeelsLike)}{tUnit}
                </div>
              )}

              {/* Rain */}
              {avgPrecipProb != null ? (
                <div className="text-sky-400 text-xs">💧 {avgPrecipProb}%</div>
              ) : day.precipitation_mm > 0.1 ? (
                <div className="text-sky-400 text-xs">🌧 {day.precipitation_mm.toFixed(1)}mm</div>
              ) : null}

              {/* Source dots */}
              {daySources.length > 0 && (
                <div className="flex gap-1 mt-0.5 flex-wrap justify-center">
                  {daySources.map((src) => (
                    <span
                      key={src}
                      className={`w-1.5 h-1.5 rounded-full ${SOURCE_COLOURS[src] || "bg-slate-400"}`}
                      title={src.replace(/_/g, " ")}
                    />
                  ))}
                </div>
              )}

              {/* Sunrise */}
              {day.sunrise && (
                <div className="text-yellow-500/70 text-xs">
                  🌅 {day.sunrise.slice(-5)}
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Week average */}
      <div className="flex items-center gap-2 px-1 text-xs text-slate-500">
        <div className="flex-1 h-px bg-red-400/20" />
        <span>
          Week avg:{" "}
          <span className="text-red-400 font-semibold">{fmt(weekAvg)}{tUnit}</span>
        </span>
        <div className="flex-1 h-px bg-red-400/20" />
      </div>
    </div>
  );
}