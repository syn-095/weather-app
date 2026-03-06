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
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true });
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

const CHART_TYPES = [
  { key: "temperature",   label: "Temp",   icon: "🌡" },
  { key: "precipitation", label: "Precip", icon: "🌧" },
  { key: "wind",          label: "Wind",   icon: "💨" },
  { key: "cards",         label: "Cards",  icon: "🃏" },
];

export default function HourlyForecast() {
  const { hourlyForDay, fmt, fmtWind, tUnit, wUnit, forecastStatus } = useWeather();
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
  const nowIndex     = getCurrentHourIndex(hourlyForDay);
  const isToday      = nowFraction !== null;

  // Tag each point as past/future
  const chartData = hourlyForDay.map((h, i) => ({
    time:         formatHour(h.time),
    Temp:         fmt(h.temperature_c),
    "Feels Like": h.feels_like_c != null && h.feels_like_c !== 0 ? fmt(h.feels_like_c) : null,
    Precip:       h.precipitation_mm ?? 0,
    Probability:  h.precipitation_probability ?? null,
    Wind:         fmtWind(h.wind_speed_kmh),
    isPast:       isToday && nowIndex !== null && i < nowIndex,
    isNow:        i === nowIndex && isToday,
  }));

  // Split into two series for past and future so we can style them independently
  // Past points get null for future series and vice versa
  const chartDataSplit = chartData.map((d, i) => ({
    ...d,
    TempPast:         d.isPast || d.isNow ? d.Temp         : null,
    TempFuture:       !d.isPast           ? d.Temp         : null,
    FeelsPast:        d.isPast || d.isNow ? d["Feels Like"]: null,
    FeelsFuture:      !d.isPast           ? d["Feels Like"]: null,
    WindPast:         d.isPast || d.isNow ? d.Wind         : null,
    WindFuture:       !d.isPast           ? d.Wind         : null,
  }));

  const validHumidity = hourlyForDay.filter((h) => h.humidity_pct > 0);
  const avgHumidity   = validHumidity.length
    ? Math.round(validHumidity.reduce((s, h) => s + h.humidity_pct, 0) / validHumidity.length)
    : null;
  const avgWind     = Math.round(hourlyForDay.reduce((s, h) => s + (h.wind_speed_kmh || 0), 0) / hourlyForDay.length);
  const totalPrecip = hourlyForDay.reduce((s, h) => s + (h.precipitation_mm || 0), 0);
  const temps       = hourlyForDay.map((h) => h.temperature_c);
  const dayAvgTemp  = fmt((Math.max(...temps) + Math.min(...temps)) / 2);

  const xProps = { dataKey: "time", tick: { fill: "#64748b", fontSize: 10 }, tickLine: false, axisLine: false, interval: 2 };
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

      {/* ── Temperature ── */}
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
              {/* Past: dim stroke + dim fill */}
              <Area type="monotone" dataKey="FeelsPast"   stroke="#a78bfa" strokeWidth={1.5} strokeOpacity={0.3} fill="url(#feelsPast)"   dot={false} connectNulls legendType="none" />
              <Area type="monotone" dataKey="TempPast"    stroke="#38bdf8" strokeWidth={2}   strokeOpacity={0.3} fill="url(#tempPast)"    dot={false} connectNulls legendType="none" />
              {/* Future: full brightness */}
              <Area type="monotone" dataKey="FeelsFuture" stroke="#a78bfa" strokeWidth={1.5} strokeOpacity={1}   fill="url(#feelsFuture)" dot={false} connectNulls legendType="none" />
              <Area type="monotone" dataKey="TempFuture"  stroke="#38bdf8" strokeWidth={2}   strokeOpacity={1}   fill="url(#tempFuture)"  dot={false} connectNulls legendType="none" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Precipitation ── */}
      {activeChart === "precipitation" && (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid {...grid} />
              <XAxis {...xProps} />
              <YAxis yAxisId="mm"  {...yProps} tickFormatter={(v) => `${v}mm`} />
              <YAxis yAxisId="pct" orientation="right" {...yProps} tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
              <Tooltip content={<PrecipTooltip />} />
              <Bar yAxisId="mm" dataKey="Precip" radius={[3,3,0,0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill="#38bdf8" fillOpacity={entry.isPast ? 0.15 : 0.7} />
                ))}
              </Bar>
              <Area yAxisId="pct" type="monotone" dataKey="Probability" stroke="#818cf8" strokeWidth={2} fill="none" dot={false} connectNulls />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Wind ── */}
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
              <Area type="monotone" dataKey="WindPast"   stroke="#2dd4bf" strokeWidth={2} strokeOpacity={0.3} fill="url(#windPast)"   dot={false} connectNulls legendType="none" />
              <Area type="monotone" dataKey="WindFuture" stroke="#2dd4bf" strokeWidth={2} strokeOpacity={1}   fill="url(#windFuture)" dot={false} connectNulls legendType="none" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Cards ── */}
      {activeChart === "cards" && (
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
          {hourlyForDay.map((h, i) => {
            const { isPast, isNow } = chartData[i];
            return (
              <div
                key={i}
                className={`flex-shrink-0 w-20 rounded-2xl p-3 border flex flex-col
                           items-center gap-2 text-center transition-all
                           ${isNow  ? "bg-amber-500/10 border-amber-500/30 scale-105"
                           : isPast ? "bg-white/[0.02] border-white/5 opacity-40"
                                    : "bg-white/5 border-white/10 hover:bg-white/10"}`}
              >
                {isNow && <span className="text-amber-400 text-xs font-bold leading-none">NOW</span>}
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