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
  Cell,
} from "recharts";

function formatHour(timeStr) {
  const d = new Date(timeStr);
  return d.toLocaleTimeString([], { hour: "numeric", hour12: true });
}

function getNowFraction(hourlyForDay) {
  if (!hourlyForDay.length) return null;
  const now      = new Date();
  const dayStart = new Date(hourlyForDay[0].time);
  const dayEnd   = new Date(hourlyForDay[hourlyForDay.length - 1].time);
  if (now < dayStart || now > dayEnd) return null;
  return (now - dayStart) / (dayEnd - dayStart);
}

function getCurrentHourIndex(hourlyForDay) {
  if (!hourlyForDay.length) return null;
  const now = new Date();
  const dayStart = new Date(hourlyForDay[0].time);
  const dayEnd   = new Date(hourlyForDay[hourlyForDay.length - 1].time);
  if (now < dayStart || now > dayEnd) return null;
  let closest = 0, closestDiff = Infinity;
  for (let i = 0; i < hourlyForDay.length; i++) {
    const diff = Math.abs(new Date(hourlyForDay[i].time) - now);
    if (diff < closestDiff) { closestDiff = diff; closest = i; }
  }
  return closest;
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
          {p.name}: {p.value}{p.name === "Rain chance" ? "%" : " mm"}
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

const CHART_TYPES = [
  { key: "cards",         label: "Hourly", icon: "🕐" },
  { key: "temperature",   label: "Temp",   icon: "🌡" },
  { key: "precipitation", label: "Precip", icon: "🌧" },
  { key: "wind",          label: "Wind",   icon: "💨" },
];

export default function HourlyForecast() {
  const { hourlyForDay, fmt, fmtWind, tUnit, wUnit, forecastStatus } = useWeather();
  // Default to cards — most scannable on mobile, shows all data at once
  const [activeChart, setActiveChart] = useState("cards");

  if (forecastStatus === "loading") {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-14 rounded-2xl bg-white/5 border border-white/10" />
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

  const nowFraction = getNowFraction(hourlyForDay);
  const nowIndex    = getCurrentHourIndex(hourlyForDay);
  const isToday     = nowFraction !== null;

  // Only show % probability axis/line if data actually exists
  const hasProbability = hourlyForDay.some(
    (h) => h.precipitation_probability != null && h.precipitation_probability > 0
  );

  const chartData = hourlyForDay.map((h, i) => ({
    time:         formatHour(h.time),
    Temp:         fmt(h.temperature_c),
    "Feels Like": h.feels_like_c != null && h.feels_like_c !== 0 ? fmt(h.feels_like_c) : null,
    Precip:       h.precipitation_mm ?? 0,
    Probability:  hasProbability ? (h.precipitation_probability ?? null) : null,
    Wind:         fmtWind(h.wind_speed_kmh),
    isPast:       isToday && nowIndex !== null && i < nowIndex,
    isNow:        i === nowIndex && isToday,
  }));

  const chartDataSplit = chartData.map((d) => ({
    ...d,
    TempPast:    d.isPast || d.isNow ? d.Temp          : null,
    TempFuture:  !d.isPast           ? d.Temp          : null,
    FeelsPast:   d.isPast || d.isNow ? d["Feels Like"] : null,
    FeelsFuture: !d.isPast           ? d["Feels Like"] : null,
    WindPast:    d.isPast || d.isNow ? d.Wind          : null,
    WindFuture:  !d.isPast           ? d.Wind          : null,
  }));

  const validHumidity = hourlyForDay.filter((h) => h.humidity_pct > 0);
  const avgHumidity   = validHumidity.length
    ? Math.round(validHumidity.reduce((s, h) => s + h.humidity_pct, 0) / validHumidity.length)
    : null;
  const avgWind     = Math.round(hourlyForDay.reduce((s, h) => s + (h.wind_speed_kmh || 0), 0) / hourlyForDay.length);
  const totalPrecip = hourlyForDay.reduce((s, h) => s + (h.precipitation_mm || 0), 0);
  const temps       = hourlyForDay.map((h) => h.temperature_c);
  const dayAvgTemp  = fmt((Math.max(...temps) + Math.min(...temps)) / 2);

  // Fewer x-axis labels on mobile to prevent overlap
  const xInterval = hourlyForDay.length > 16 ? 3 : 2;
  const xProps = {
    dataKey: "time",
    tick: { fill: "#64748b", fontSize: 10 },
    tickLine: false,
    axisLine: false,
    interval: xInterval,
  };
  const yProps = { tick: { fill: "#64748b", fontSize: 10 }, tickLine: false, axisLine: false };
  const grid   = { strokeDasharray: "3 3", stroke: "rgba(255,255,255,0.05)" };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <SummaryChip label="Avg Humidity" value={avgHumidity != null ? `${avgHumidity}%` : "—"} color="text-blue-300" />
        <SummaryChip label="Avg Temp"     value={`${dayAvgTemp}${tUnit}`}                       color="text-red-300"  />
        <SummaryChip label="Total Precip" value={`${totalPrecip.toFixed(1)} mm`}                color="text-sky-300"  />
      </div>

      <div className="flex gap-1 p-1 bg-white/5 rounded-2xl border border-white/10">
        {CHART_TYPES.map((ct) => (
          <button
            key={ct.key}
            onClick={() => setActiveChart(ct.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-xl
                        text-xs font-semibold transition-all duration-200
                        ${activeChart === ct.key
                          ? "bg-sky-500/30 text-sky-300 border border-sky-500/40"
                          : "text-slate-400 hover:text-slate-300 hover:bg-white/5"}`}
          >
            <span>{ct.icon}</span>
            <span className="hidden sm:inline">{ct.label}</span>
          </button>
        ))}
      </div>

      {/* ── Hourly table — all data at a glance, mobile-first ── */}
      {activeChart === "cards" && (
        <div className="overflow-x-auto -mx-1 px-1">
          <table className="w-full min-w-max text-xs border-collapse">
            <thead>
              <tr className="text-slate-500 uppercase tracking-wider text-left">
                <th className="pb-2 pr-4 font-medium">Time</th>
                <th className="pb-2 pr-3 font-medium text-center">Sky</th>
                <th className="pb-2 pr-4 font-medium">Temp</th>
                <th className="pb-2 pr-4 font-medium">Feels</th>
                <th className="pb-2 pr-4 font-medium">Rain</th>
                <th className="pb-2 font-medium">Wind</th>
              </tr>
            </thead>
            <tbody>
              {hourlyForDay.map((h, i) => {
                const { isPast, isNow } = chartData[i];
                return (
                  <tr
                    key={i}
                    className={`border-t border-white/5
                      ${isNow  ? "bg-amber-500/10"
                      : isPast ? "opacity-35"
                               : ""}`}
                  >
                    <td className={`py-2.5 pr-4 font-mono font-semibold whitespace-nowrap
                      ${isNow ? "text-amber-300" : isPast ? "text-slate-600" : "text-slate-300"}`}>
                      {isNow ? "NOW" : formatHour(h.time)}
                    </td>
                    <td className="py-2.5 pr-3 text-center">
                      <WeatherIcon icon={h.icon} className="w-4 h-4 inline-block" />
                    </td>
                    <td className={`py-2.5 pr-4 font-semibold whitespace-nowrap
                      ${isPast ? "text-slate-500" : "text-white"}`}>
                      {fmt(h.temperature_c)}{tUnit}
                    </td>
                    <td className="py-2.5 pr-4 text-slate-400 whitespace-nowrap">
                      {h.feels_like_c != null && h.feels_like_c !== 0
                        ? `${fmt(h.feels_like_c)}${tUnit}`
                        : "—"}
                    </td>
                    <td className="py-2.5 pr-4 whitespace-nowrap">
                      {h.precipitation_mm > 0.05
                        ? <span className="text-sky-400">{h.precipitation_mm.toFixed(1)}mm</span>
                        : <span className="text-slate-700">—</span>}
                    </td>
                    <td className="py-2.5 whitespace-nowrap text-slate-300">
                      {fmtWind(h.wind_speed_kmh)}<span className="text-slate-500 text-xs ml-0.5">{wUnit}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Temperature chart ── */}
      {activeChart === "temperature" && (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartDataSplit} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="tempFuture" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#38bdf8" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}   />
                </linearGradient>
                <linearGradient id="tempPast" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#38bdf8" stopOpacity={0.08} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}    />
                </linearGradient>
                <linearGradient id="feelsFuture" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#a78bfa" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#a78bfa" stopOpacity={0}   />
                </linearGradient>
                <linearGradient id="feelsPast" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#a78bfa" stopOpacity={0.05} />
                  <stop offset="95%" stopColor="#a78bfa" stopOpacity={0}    />
                </linearGradient>
              </defs>
              <CartesianGrid {...grid} />
              <XAxis {...xProps} />
              <YAxis {...yProps} tickFormatter={(v) => `${v}${tUnit}`} />
              <Tooltip content={<TempTooltip tUnit={tUnit} />} />
              <ReferenceLine
                y={dayAvgTemp} stroke="#f87171" strokeDasharray="4 4" strokeWidth={1.5}
                label={{ value: `avg ${dayAvgTemp}${tUnit}`, fill: "#f87171", fontSize: 10, position: "insideTopRight" }}
              />
              <Area type="monotone" dataKey="FeelsPast"   name="Feels like"   stroke="#a78bfa" strokeWidth={1.5} strokeOpacity={0.3} fill="url(#feelsPast)"   dot={false} connectNulls legendType="none" />
              <Area type="monotone" dataKey="TempPast"    name="Temperature"  stroke="#38bdf8" strokeWidth={2}   strokeOpacity={0.3} fill="url(#tempPast)"    dot={false} connectNulls legendType="none" />
              <Area type="monotone" dataKey="FeelsFuture" name="Feels like"   stroke="#a78bfa" strokeWidth={1.5} strokeOpacity={1}   fill="url(#feelsFuture)" dot={false} connectNulls legendType="none" />
              <Area type="monotone" dataKey="TempFuture"  name="Temperature"  stroke="#38bdf8" strokeWidth={2}   strokeOpacity={1}   fill="url(#tempFuture)"  dot={false} connectNulls legendType="none" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Precipitation chart ── */}
      {activeChart === "precipitation" && (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid {...grid} />
              <XAxis {...xProps} />
              <YAxis yAxisId="mm" {...yProps} tickFormatter={(v) => `${v}mm`} />
              {/* Only render % axis when data actually exists */}
              {hasProbability && (
                <YAxis yAxisId="pct" orientation="right" {...yProps} tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
              )}
              <Tooltip content={<PrecipTooltip />} />
              <Bar yAxisId="mm" dataKey="Precip" name="Precipitation" radius={[3,3,0,0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill="#38bdf8" fillOpacity={entry.isPast ? 0.15 : 0.7} />
                ))}
              </Bar>
              {hasProbability && (
                <Area yAxisId="pct" type="monotone" dataKey="Probability" name="Rain chance" stroke="#818cf8" strokeWidth={2} fill="none" dot={false} connectNulls />
              )}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Wind chart ── */}
      {activeChart === "wind" && (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartDataSplit} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="windFuture" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#2dd4bf" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#2dd4bf" stopOpacity={0}   />
                </linearGradient>
                <linearGradient id="windPast" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#2dd4bf" stopOpacity={0.08} />
                  <stop offset="95%" stopColor="#2dd4bf" stopOpacity={0}    />
                </linearGradient>
              </defs>
              <CartesianGrid {...grid} />
              <XAxis {...xProps} />
              <YAxis {...yProps} />
              <Tooltip content={<WindTooltip wUnit={wUnit} />} />
              <ReferenceLine
                y={fmtWind(avgWind)} stroke="#f87171" strokeDasharray="4 4" strokeWidth={1.5}
                label={{ value: `avg ${fmtWind(avgWind)} ${wUnit}`, fill: "#f87171", fontSize: 10, position: "insideTopRight" }}
              />
              <Area type="monotone" dataKey="WindPast"   name="Wind" stroke="#2dd4bf" strokeWidth={2} strokeOpacity={0.3} fill="url(#windPast)"   dot={false} connectNulls legendType="none" />
              <Area type="monotone" dataKey="WindFuture" name="Wind" stroke="#2dd4bf" strokeWidth={2} strokeOpacity={1}   fill="url(#windFuture)" dot={false} connectNulls legendType="none" />
            </AreaChart>
          </ResponsiveContainer>
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