import React, { useState } from "react";
import { useWeather } from "../hooks/useWeather";
import WeatherIcon from "./WeatherIcon";
import {
  ResponsiveContainer,
  AreaChart,
  BarChart,
  Area,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";

function formatHour(timeStr) {
  const d = new Date(timeStr);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true });
}

function TempTooltip({ active, payload, label, tUnit }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900/95 border border-white/10 rounded-xl px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p) => p.value != null && (
        <p key={p.name} style={{ color: p.color }} className="font-semibold">
          {p.name}: {p.value}{tUnit}
        </p>
      ))}
    </div>
  );
}

function PrecipTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900/95 border border-white/10 rounded-xl px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p) => p.value != null && (
        <p key={p.name} style={{ color: p.color }} className="font-semibold">
          {p.name}: {p.value}{p.name === "Probability" ? "%" : " mm"}
        </p>
      ))}
    </div>
  );
}

function AvgTempTooltip({ active, payload, label, tUnit }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900/95 border border-white/10 rounded-xl px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p) => p.value != null && (
        <p key={p.name} style={{ color: p.color }} className="font-semibold">
          {p.name}: {p.value}{tUnit}
        </p>
      ))}
    </div>
  );
}

const CHART_TYPES = [
  { key: "temperature",   label: "Temp",    icon: "🌡" },
  { key: "precipitation", label: "Precip",  icon: "🌧" },
  { key: "avgtemp",       label: "Avg Temp", icon: "📊" },
  { key: "cards",         label: "Cards",   icon: "🃏" },
];

export default function HourlyForecast() {
  const {
    hourlyForDay, selectedDay,
    fmt, fmtWind, tUnit, wUnit,
    forecastStatus,
  } = useWeather();

  const [activeChart, setActiveChart] = useState("temperature");

  if (forecastStatus === "loading") {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
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

  // Build chart data
  const chartData = hourlyForDay.map((h) => ({
    time:        formatHour(h.time),
    Temp:        fmt(h.temperature_c),
    "Feels Like": h.feels_like_c != null && h.feels_like_c !== 0
                   ? fmt(h.feels_like_c)
                   : null,
    Precip:      h.precipitation_mm ?? 0,
    Probability: h.precipitation_probability ?? null,
  }));

  // Rolling 3-hour average temperature for the avg temp chart
  const avgTempData = chartData.map((d, i, arr) => {
    const window = arr.slice(Math.max(0, i - 1), Math.min(arr.length, i + 2));
    const validTemps = window.map((w) => w.Temp).filter((t) => t != null);
    const rollingAvg = validTemps.length
      ? Math.round((validTemps.reduce((s, t) => s + t, 0) / validTemps.length) * 10) / 10
      : null;
    return {
      time: d.time,
      Temp: d.Temp,
      "3hr Rolling Avg": rollingAvg,
      "Feels Like": d["Feels Like"],
    };
  });

  // Summary stats
  const validHumidity = hourlyForDay.filter((h) => h.humidity_pct > 0);
  const avgHumidity = validHumidity.length
    ? Math.round(validHumidity.reduce((s, h) => s + h.humidity_pct, 0) / validHumidity.length)
    : null;
  const avgWind = Math.round(
    hourlyForDay.reduce((s, h) => s + (h.wind_speed_kmh || 0), 0) / hourlyForDay.length
  );
  const totalPrecip = hourlyForDay.reduce((s, h) => s + (h.precipitation_mm || 0), 0);

  // Day average temp for reference line
  const dayAvgTemp = fmt(
    hourlyForDay.reduce((s, h) => s + h.temperature_c, 0) / hourlyForDay.length
  );

  return (
    <div className="space-y-4">
      {/* Summary chips */}
      <div className="grid grid-cols-3 gap-2">
        <SummaryChip label="Avg Humidity" value={avgHumidity != null ? `${avgHumidity}%` : "—"} color="text-blue-300"  />
        <SummaryChip label="Avg Wind"     value={`${fmtWind(avgWind)} ${wUnit}`}               color="text-teal-300"  />
        <SummaryChip label="Total Precip" value={`${totalPrecip.toFixed(1)} mm`}               color="text-sky-300"   />
      </div>

      {/* Toggle */}
      <div className="flex gap-1 p-1 bg-white/5 rounded-2xl border border-white/10">
        {CHART_TYPES.map((ct) => (
          <button
            key={ct.key}
            onClick={() => setActiveChart(ct.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-xl
                        text-xs font-semibold transition-all duration-200
                        ${activeChart === ct.key
                          ? "bg-sky-500/30 text-sky-300 border border-sky-500/40"
                          : "text-slate-400 hover:text-slate-300 hover:bg-white/5"
                        }`}
          >
            <span>{ct.icon}</span>
            <span className="hidden sm:inline">{ct.label}</span>
          </button>
        ))}
      </div>

      {/* Temperature chart */}
      {activeChart === "temperature" && (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#38bdf8" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}   />
                </linearGradient>
                <linearGradient id="feelsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#a78bfa" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#a78bfa" stopOpacity={0}   />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} interval={2} />
              <YAxis tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}${tUnit}`} />
              <Tooltip content={<TempTooltip tUnit={tUnit} />} />
              <ReferenceLine
                y={dayAvgTemp}
                stroke="#f87171"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: `avg ${dayAvgTemp}${tUnit}`, fill: "#f87171", fontSize: 10, position: "insideTopRight" }}
              />
              <Area type="monotone" dataKey="Feels Like" stroke="#a78bfa" strokeWidth={1.5} fill="url(#feelsGrad)" dot={false} connectNulls />
              <Area type="monotone" dataKey="Temp"       stroke="#38bdf8" strokeWidth={2}   fill="url(#tempGrad)"  dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Precipitation chart */}
      {activeChart === "precipitation" && (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} interval={2} />
              <YAxis yAxisId="mm"  tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}mm`} />
              <YAxis yAxisId="pct" orientation="right" tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
              <Tooltip content={<PrecipTooltip />} />
              <Bar  yAxisId="mm"  dataKey="Precip"      fill="#38bdf8" fillOpacity={0.7} radius={[3,3,0,0]} />
              <Area yAxisId="pct" dataKey="Probability" stroke="#818cf8" strokeWidth={2} fill="none" dot={false} connectNulls type="monotone" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Average temperature chart — rolling 3hr avg vs raw temp vs feels like */}
      {activeChart === "avgtemp" && (
        <div className="space-y-1">
          <p className="text-xs text-slate-500 px-1">
            Hourly temp (blue) · 3-hour rolling average (red dashed) · feels like (purple)
          </p>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={avgTempData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="avgTempGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#38bdf8" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}    />
                  </linearGradient>
                  <linearGradient id="feelsGrad2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#a78bfa" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#a78bfa" stopOpacity={0}    />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} interval={2} />
                <YAxis tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}${tUnit}`} />
                <Tooltip content={<AvgTempTooltip tUnit={tUnit} />} />
                <ReferenceLine
                  y={dayAvgTemp}
                  stroke="#f87171"
                  strokeDasharray="4 4"
                  strokeWidth={2}
                  label={{ value: `day avg ${dayAvgTemp}${tUnit}`, fill: "#f87171", fontSize: 10, position: "insideTopRight" }}
                />
                <Area type="monotone" dataKey="Feels Like"      stroke="#a78bfa" strokeWidth={1.5} strokeDasharray="3 3" fill="url(#feelsGrad2)" dot={false} connectNulls />
                <Area type="monotone" dataKey="Temp"            stroke="#38bdf8" strokeWidth={1.5} fill="url(#avgTempGrad)" dot={false} />
                <Area type="monotone" dataKey="3hr Rolling Avg" stroke="#f87171" strokeWidth={2.5} fill="none" dot={false} connectNulls />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Cards view */}
      {activeChart === "cards" && (
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
              <span className="text-slate-500 text-xs">
                {fmtWind(h.wind_speed_kmh)}{wUnit.replace("km/", "")}
              </span>
            </div>
          ))}
        </div>
      )}
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