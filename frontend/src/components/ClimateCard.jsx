import React from "react";
import { useSelector } from "react-redux";
import { useWeather } from "../hooks/useWeather";

export default function ClimateCard() {
  const climate = useSelector((s) => s.weather.climateNormals);
  const { fmt, tUnit } = useWeather();

  if (!climate?.monthly_normals?.length) return null;

  const normals = climate.monthly_normals;
  const maxTemp = Math.max(...normals.map((m) => m.temp_max_c ?? -Infinity));
  const minTemp = Math.min(...normals.map((m) => m.temp_min_c ?? Infinity));
  const tempRange = maxTemp - minTemp || 1;

  return (
    <div className="rounded-3xl p-5 bg-white/5 border border-white/10 backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400">
          📊 Climate Normals (30yr avg)
        </h2>
        <span className="text-xs text-slate-600">ERA5 1991–2020</span>
      </div>

      {/* Monthly bar chart */}
      <div className="flex items-end gap-1 h-24">
        {normals.map((m) => {
          const heightPct = m.temp_max_c != null
            ? ((m.temp_max_c - minTemp) / tempRange) * 80 + 20
            : 20;
          return (
            <div key={m.month} className="flex-1 flex flex-col items-center gap-1 group">
              <div className="relative w-full flex flex-col justify-end" style={{ height: "80px" }}>
                {/* Tooltip */}
                <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2
                               bg-slate-800 text-white text-xs rounded-lg px-2 py-1
                               opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10 pointer-events-none">
                  {m.month_name}: {fmt(m.temp_max_c ?? 0)}/{fmt(m.temp_min_c ?? 0)}{tUnit}
                </div>
                <div
                  className="w-full rounded-t-lg bg-gradient-to-t from-sky-600/60 to-sky-400/40
                             hover:from-sky-500/80 hover:to-sky-300/60 transition-colors cursor-default"
                  style={{ height: `${heightPct}%` }}
                />
              </div>
              <span className="text-slate-500 text-xs">{m.month_name.slice(0, 1)}</span>
            </div>
          );
        })}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2">
        <ClimateStat
          label="Hottest month"
          value={normals.reduce((a, b) => (a.temp_max_c ?? -Infinity) > (b.temp_max_c ?? -Infinity) ? a : b).month_name}
        />
        <ClimateStat
          label="Wettest month"
          value={normals.reduce((a, b) => (a.precipitation_mm ?? 0) > (b.precipitation_mm ?? 0) ? a : b).month_name}
        />
        <ClimateStat
          label="Avg annual"
          value={`${fmt(normals.reduce((s, m) => s + (m.temp_mean_c ?? 0), 0) / normals.length)}${tUnit}`}
        />
      </div>
    </div>
  );
}

function ClimateStat({ label, value }) {
  return (
    <div className="bg-white/5 rounded-2xl px-3 py-2 border border-white/10 text-center">
      <div className="text-slate-500 text-xs mb-0.5">{label}</div>
      <div className="text-white text-sm font-bold">{value}</div>
    </div>
  );
}