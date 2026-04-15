import React from "react";
import { useSelector } from "react-redux";

function WaveDirection({ degrees }) {
  if (degrees == null) return null;
  return (
    <span
      className="inline-block text-sky-400"
      style={{ transform: `rotate(${degrees}deg)` }}
      title={`${degrees}°`}
    >
      ↑
    </span>
  );
}

export default function MarineCard() {
  const marine = useSelector((s) => s.weather.marine);

  if (!marine) return null;

  const current = marine.hourly?.[0] || {};
  const daily = marine.daily || [];

  return (
    <div className="rounded-3xl p-5 bg-white/5 border border-white/10 space-y-4">
      <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400">
        🌊 Marine Forecast
      </h2>

      {/* Current marine conditions */}
      <div className="grid grid-cols-2 gap-3">
        <MarineStat
          icon="🌊"
          label="Wave Height"
          value={current.wave_height != null ? `${current.wave_height.toFixed(1)} m` : "—"}
        />
        <MarineStat
          icon="🌡"
          label="Sea Temp"
          value={current.sea_surface_temperature != null
            ? `${current.sea_surface_temperature.toFixed(1)}°C`
            : "—"}
        />
        <MarineStat
          icon="⏱"
          label="Wave Period"
          value={current.wave_period != null ? `${current.wave_period.toFixed(0)} s` : "—"}
        />
        <MarineStat
          icon="🌬"
          label="Swell Height"
          value={current.swell_wave_height != null
            ? `${current.swell_wave_height.toFixed(1)} m`
            : "—"}
        />
      </div>

      {/* Daily max waves */}
      {daily.length > 0 && (
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Daily Max Waves</p>
          <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-1">
            {daily.slice(0, 7).map((d) => (
              <div
                key={d.date}
                className="flex-shrink-0 text-center bg-white/5 rounded-2xl px-3 py-2 border border-white/10 min-w-[70px]"
              >
                <div className="text-xs text-slate-400 mb-1">
                  {new Date(d.date + "T12:00:00").toLocaleDateString([], { weekday: "short" })}
                </div>
                <div className="text-white text-sm font-bold">
                  {d.wave_height_max != null ? `${d.wave_height_max.toFixed(1)}m` : "—"}
                </div>
                <div className="text-slate-500 text-xs">
                  {d.swell_wave_height_max != null ? `↑${d.swell_wave_height_max.toFixed(1)}m` : ""}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MarineStat({ icon, label, value }) {
  return (
    <div className="bg-white/5 rounded-2xl px-3 py-2.5 border border-white/10">
      <div className="text-lg leading-none mb-1">{icon}</div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="text-sm font-semibold text-white">{value}</div>
    </div>
  );
}