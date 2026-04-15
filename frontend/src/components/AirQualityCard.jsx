import React from "react";
import { useSelector } from "react-redux";

const AQI_COLORS = {
  "Good": "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  "Fair": "text-green-400 bg-green-500/10 border-green-500/20",
  "Moderate": "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
  "Poor": "text-orange-400 bg-orange-500/10 border-orange-500/20",
  "Very Poor": "text-red-400 bg-red-500/10 border-red-500/20",
  "Extremely Poor": "text-purple-400 bg-purple-500/10 border-purple-500/20",
};

function aqiLabel(aqi) {
  if (aqi == null) return "Unknown";
  if (aqi <= 20) return "Good";
  if (aqi <= 40) return "Fair";
  if (aqi <= 60) return "Moderate";
  if (aqi <= 80) return "Poor";
  if (aqi <= 100) return "Very Poor";
  return "Extremely Poor";
}

function PollenBar({ label, value }) {
  if (value == null) return null;
  const pct = Math.min((value / 100) * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="text-white font-medium">{Math.round(value)}</span>
      </div>
      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full bg-emerald-400/70 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function AirQualityCard() {
  const airQuality = useSelector((s) => s.weather.airQuality);

  if (!airQuality) return null;

  const current = airQuality.current || {};
  const label = aqiLabel(current.european_aqi);
  const colorClass = AQI_COLORS[label] || "text-slate-300 bg-white/5 border-white/10";

  return (
    <div className="rounded-3xl p-5 bg-white/5 border border-white/10 space-y-4">
      <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400">
        Air Quality
      </h2>

      {/* AQI badge */}
      <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-2xl border ${colorClass}`}>
        <span className="text-2xl font-black">{Math.round(current.european_aqi ?? 0)}</span>
        <span className="text-sm font-semibold">{label}</span>
      </div>

      {/* Pollutants grid */}
      <div className="grid grid-cols-2 gap-3">
        <Pollutant label="PM2.5" value={current.pm2_5} unit="μg/m³" />
        <Pollutant label="PM10" value={current.pm10} unit="μg/m³" />
        <Pollutant label="Ozone" value={current.ozone} unit="μg/m³" />
        <Pollutant label="NO₂" value={current.nitrogen_dioxide} unit="μg/m³" />
      </div>

      {/* UV Index */}
      {current.uv_index != null && (
        <div className="flex items-center justify-between p-3 rounded-2xl bg-white/5 border border-white/10">
          <div className="flex items-center gap-2">
            <span className="text-xl">☀️</span>
            <span className="text-sm text-slate-300">UV Index</span>
          </div>
          <div className="text-right">
            <span className="text-white font-bold text-lg">{current.uv_index?.toFixed(1)}</span>
            <span className="text-slate-400 text-xs ml-1">{uvLabel(current.uv_index)}</span>
          </div>
        </div>
      )}

      {/* Pollen */}
      {(current.grass_pollen != null || current.birch_pollen != null || current.alder_pollen != null) && (
        <div className="space-y-2">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Pollen</p>
          <PollenBar label="Grass" value={current.grass_pollen} />
          <PollenBar label="Birch" value={current.birch_pollen} />
          <PollenBar label="Alder" value={current.alder_pollen} />
        </div>
      )}
    </div>
  );
}

function Pollutant({ label, value, unit }) {
  if (value == null) return null;
  return (
    <div className="bg-white/5 rounded-2xl px-3 py-2.5 border border-white/10">
      <div className="text-xs text-slate-400 mb-0.5">{label}</div>
      <div className="text-white font-semibold text-sm">
        {value.toFixed(1)} <span className="text-slate-500 text-xs font-normal">{unit}</span>
      </div>
    </div>
  );
}

function uvLabel(uv) {
  if (uv == null) return "";
  if (uv < 3) return "Low";
  if (uv < 6) return "Moderate";
  if (uv < 8) return "High";
  if (uv < 11) return "Very High";
  return "Extreme";
}