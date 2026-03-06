import React, { useState, useMemo } from "react";
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
  Cell,
} from "recharts";

function formatHour(timeStr) {
  const d = new Date(timeStr);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true });
}

// Returns 0–1 fraction of how far through the selected day we are.
// Returns null if the selected day is not today.
function getNowFraction(hourlyForDay) {
  if (!hourlyForDay.length) return null;
  const now      = new Date();
  const dayStart = new Date(hourlyForDay[0].time);
  const dayEnd   = new Date(hourlyForDay[hourlyForDay.length - 1].time);
  if (now < dayStart || now > dayEnd) return null;
  return (now - dayStart) / (dayEnd - dayStart);
}

function getCurrentHourLabel(hourlyForDay) {
  const now = new Date();
  const dayStart = new Date(hourlyForDay[0]?.time);
  const dayEnd   = new Date(hourlyForDay[hourlyForDay.length - 1]?.time);
  if (now < dayStart || now > dayEnd) return null;
  let closest = null, closestDiff = Infinity;
  for (const h of hourlyForDay) {
    const diff = Math.abs(new Date(h.time) - now);
    if (diff < closestDiff) { closestDiff = diff; closest = h; }
  }
  return closest ? formatHour(closest.time) : null;
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

function WindTooltip({ active, payload, label, wUnit }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900/95 border border-white/10 rounded-xl px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p) => p.value != null && (
        <p key={p.name} style={{ color: p.color }} className="font-semibold">
          {p.name}: {p.value} {wUnit}
        </p>
      ))}
    </div>
  );
}

// Gradient defs: vertical fill gradient only (no stroke gradient — Recharts doesn't support it)
// The fade effect is achieved by making the fill very dim for the whole chart on past days,
// and using two overlapping gradients anchored at nowFraction for today.
function GradientDefs({ nowFraction, color, fillId }) {
  if (nowFraction === null) {
    // Not today — full brightness fill gradient
    return (
      <>
        <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%"  stopColor={color} stopOpacity={0.35} />
          <stop offset="95%" stopColor={color} stopOpacity={0}    />
        </linearGradient>
      </>
    );
  }

  const pct = `${Math.round(nowFraction * 100)}%`;
  return (
    <>
      {/* Fill gradient: past portion dim, future portion bright */}
      <linearGradient id={fillId} x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%"   stopColor={color} stopOpacity={0.06} />
        <stop offset={pct}  stopColor={color} stopOpacity={0.06} />
        <stop offset={pct}  stopColor={color} stopOpacity={0.35} />
        <stop offset="100%" stopColor={color} stopOpacity={0.35} />
      </linearGradient>
    </>
  );
}

// Returns stroke opacity for a data point based on whether it's past/future
function strokeOpacity(index, totalPoints, nowFraction) {
  if (nowFraction === null) return 1;
  const pointFraction = index / (totalPoints - 1);
  return pointFraction < nowFraction ? 0.25 : 1;
}

// Custom dot that fades past hours — used sparingly (dot={false} on Area,
// but we use a custom activeDot)
function FadedActiveDot({ cx, cy, fill }) {
  return <circle cx={cx} cy={cy} r={4} fill={fill} stroke="white" strokeWidth={1.5} />;
}

const CHART_TYPES = [
  { key: "temperature",   label: "Temp",   icon: "🌡" },
  { key: "precipitation", label: "Precip", icon: "🌧" },
  { key: "wind",          label: "Wind",   icon: "💨" },
  { key: "cards",         label: "Cards",  icon: "🃏" },
];

export default function HourlyForecast() {
  const {
    hourlyForDay,
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

  const nowFraction  = getNowFraction(hourlyForDay);
  const nowLabel     = getCurrentHourLabel(hourlyForDay);
  const totalPoints  = hourlyForDay.length;

  // Build chart data — tag each point with its past/future opacity
  const chartData = hourlyForDay.map((h, i) => {
    const op = strokeOpacity(i, totalPoints, nowFraction);
    return {
      time:         formatHour(h.time),
      Temp:         fmt(h.temperature_c),
      "Feels Like": h.feels_like_c != null && h.feels_like_c !== 0 ? fmt(h.feels_like_c) : null,
      Precip:       h.precipitation_mm ?? 0,
      Probability:  h.precipitation_probability ?? null,
      Wind:         fmtWind(h.wind_speed_kmh),
      _opacity:     op,
      _isPast:      nowFraction !== null && op < 1,
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
  const temps       = hourlyForDay.map((h) => h.temperature_c);
  const dayAvgTemp  = fmt((Math.max(...temps) + Math.min(...temps)) / 2);

  // Shared axis / grid props
  const xAxisProps = {
    dataKey: "time",
    tick: { fill: "#64748b", fontSize: 10 },
    tickLine: false,
    axisLine: false,
    interval: 2,
  };
  const yAxisProps = {
    tick: { fill: "#64748b", fontSize: 10 },
    tickLine: false,
    axisLine: false,
  };
  const gridProps = {
    strokeDasharray: "3 3",
    stroke: "rgba(255,255,255,0.05)",
  };

  return (
    <div className="space-y-4">

      {/* Summary chips */}
      <div className="grid grid-cols-3 gap-2">
        <SummaryChip label="Avg Humidity" value={avgHumidity != null ? `${avgHumidity}%` : "—"} color="text-blue-300" />
        <SummaryChip label="Avg Temp"     value={`${dayAvgTemp}${tUnit}`}                       color="text-red-300"  />
        <SummaryChip label="Total Precip" value={`${totalPrecip.toFixed(1)} mm`}                color="text-sky-300"  />
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

      {/* ── Temperature ── */}
      {activeChart === "temperature" && (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <GradientDefs nowFraction={nowFraction} color="#38bdf8" fillId="tempFill" />
                <GradientDefs nowFraction={nowFraction} color="#a78bfa" fillId="feelsFill" />
              </defs>
              <CartesianGrid {...gridProps} />
              <XAxis {...xAxisProps} />
              <YAxis {...yAxisProps} tickFormatter={(v) => `${v}${tUnit}`} />
              <Tooltip content={<TempTooltip tUnit={tUnit} />} />
              <ReferenceLine
                y={dayAvgTemp}
                stroke="#f87171"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: `avg ${dayAvgTemp}${tUnit}`, fill: "#f87171", fontSize: 10, position: "insideTopRight" }}
              />
              <Area
                type="monotone"
                dataKey="Feels Like"
                stroke="#a78bfa"
                strokeWidth={1.5}
                strokeOpacity={0.7}
                fill="url(#feelsFill)"
                dot={false}
                connectNulls
              />
              <Area
                type="monotone"
                dataKey="Temp"
                stroke="#38bdf8"
                strokeWidth={2}
                fill="url(#tempFill)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Precipitation ── */}
      {activeChart === "precipitation" && (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid {...gridProps} />
              <XAxis {...xAxisProps} />
              <YAxis yAxisId="mm"  {...yAxisProps} tickFormatter={(v) => `${v}mm`} />
              <YAxis yAxisId="pct" orientation="right" {...yAxisProps} tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
              <Tooltip content={<PrecipTooltip />} />
              <Bar yAxisId="mm" dataKey="Precip" radius={[3,3,0,0]}>
                {chartData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill="#38bdf8"
                    fillOpacity={entry._isPast ? 0.2 : 0.7}
                  />
                ))}
              </Bar>
              <Area
                yAxisId="pct"
                type="monotone"
                dataKey="Probability"
                stroke="#818cf8"
                strokeWidth={2}
                strokeOpacity={0.8}
                fill="none"
                dot={false}
                connectNulls
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Wind ── */}
      {activeChart === "wind" && (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <GradientDefs nowFraction={nowFraction} color="#2dd4bf" fillId="windFill" />
              </defs>
              <CartesianGrid {...gridProps} />
              <XAxis {...xAxisProps} />
              <YAxis {...yAxisProps} />
              <Tooltip content={<WindTooltip wUnit={wUnit} />} />
              <ReferenceLine
                y={fmtWind(avgWind)}
                stroke="#f87171"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{ value: `avg ${fmtWind(avgWind)} ${wUnit}`, fill: "#f87171", fontSize: 10, position: "insideTopRight" }}
              />
              <Area
                type="monotone"
                dataKey="Wind"
                stroke="#2dd4bf"
                strokeWidth={2}
                fill="url(#windFill)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Cards ── */}
      {activeChart === "cards" && (
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
          {hourlyForDay.map((h, i) => {
            const isNow  = nowLabel === formatHour(h.time);
            const isPast = chartData[i]?._isPast && !isNow;
            return (
              <div
                key={i}
                className={`flex-shrink-0 w-20 rounded-2xl p-3 border
                           flex flex-col items-center gap-2 text-center transition-all
                           ${isNow
                             ? "bg-amber-500/10 border-amber-500/30 scale-105"
                             : isPast
                             ? "bg-white/[0.02] border-white/5 opacity-40"
                             : "bg-white/5 border-white/10 hover:bg-white/10"
                           }`}
              >
                {isNow && (
                  <span className="text-amber-400 text-xs font-bold leading-none tracking-wider">NOW</span>
                )}
                <span className={`text-xs font-medium leading-none
                  ${isNow ? "text-amber-300" : isPast ? "text-slate-600" : "text-slate-400"}`}>
                  {formatHour(h.time)}
                </span>
                <div className="w-6 h-6 text-slate-300">
                  <WeatherIcon icon={h.icon} className="w-6 h-6" />
                </div>
                <span className={`text-sm font-bold ${isPast ? "text-slate-500" : "text-white"}`}>
                  {fmt(h.temperature_c)}{tUnit}
                </span>
                {h.precipitation_mm > 0.05 && (
                  <span className="text-sky-400 text-xs">{h.precipitation_mm.toFixed(1)}mm</span>
                )}
                <span className="text-slate-500 text-xs">
                  {fmtWind(h.wind_speed_kmh)}{wUnit.replace("km/", "")}
                </span>
              </div>
            );
          })}
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