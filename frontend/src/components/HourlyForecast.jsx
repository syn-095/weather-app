import React from "react";
import { useWeather } from "../hooks/useWeather";
import WeatherIcon from "./WeatherIcon";

function formatHour(timeStr) {
  const d = new Date(timeStr);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true });
}

export default function HourlyForecast() {
  const { hourlyForDay, selectedDay, fmt, fmtWind, tUnit, wUnit, forecastStatus } = useWeather();

  if (forecastStatus === "loading") {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-14 rounded-2xl bg-white/5 animate-pulse border border-white/10" />
        ))}
      </div>
    );
  }

  if (!hourlyForDay.length) {
    return (
      <div className="text-slate-500 text-sm text-center py-8">
        Select a day to see hourly data
      </div>
    );
  }

  const validHumidity = hourlyForDay.filter((h) => h.humidity_pct > 0);
  const avgHumidity = validHumidity.length
    ? Math.round(validHumidity.reduce((s, h) => s + h.humidity_pct, 0) / validHumidity.length)
    : null;
  const avgWind = Math.round(
    hourlyForDay.reduce((s, h) => s + (h.wind_speed_kmh || 0), 0) / hourlyForDay.length
  );
  const totalPrecip = hourlyForDay.reduce((s, h) => s + (h.precipitation_mm || 0), 0);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2 mb-4">
        <SummaryChip label="Avg Humidity" value={avgHumidity != null ? `${avgHumidity}%` : "—"} color="text-blue-300" />
        <SummaryChip label="Avg Wind" value={`${fmtWind(avgWind)} ${wUnit}`} color="text-teal-300" />
        <SummaryChip label="Total Precip" value={`${totalPrecip.toFixed(1)} mm`} color="text-sky-300" />
      </div>

      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
        {hourlyForDay.map((h, i) => (
          <div
            key={i}
            className="flex-shrink-0 w-20 rounded-2xl p-3 bg-white/5 border border-white/10
                       flex flex-col items-center gap-2 text-center hover:bg-white/10 transition-colors"
          >
            <span className="text-xs text-slate-400 font-medium leading-none">{formatHour(h.time)}</span>
            <div className="text-slate-300 w-6 h-6">
              <WeatherIcon icon={h.icon} className="w-6 h-6" />
            </div>
            <span className="text-white text-sm font-bold">{fmt(h.temperature_c)}{tUnit}</span>
            {h.precipitation_mm > 0.05 && (
              <span className="text-sky-400 text-xs">{h.precipitation_mm.toFixed(1)}mm</span>
            )}
            <span className="text-slate-500 text-xs">{fmtWind(h.wind_speed_kmh)}{wUnit.replace("km/", "")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SummaryChip({ label, value, color }) {
  return (
    <div className="bg-white/5 rounded-2xl px-3 py-2 border border-white/10 text-center">
      <div className="text-slate-500 text-xs mb-0.5">{label}</div>
      <div className={`text-sm font-bold ${color}`}>{value}</div>
    </div>
  );
}