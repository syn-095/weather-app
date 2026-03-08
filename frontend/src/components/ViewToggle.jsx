import React from "react";

export default function ViewToggle({ viewMode, onToggle, disabled, isOverride, elevation }) {
  return (
    <div className="flex items-center gap-2">
      {elevation != null && (
        <span className="text-xs font-mono text-sky-400/70">
          {Math.round(elevation)}m
        </span>
      )}
      <button
        onClick={onToggle}
        disabled={disabled}
        title={disabled ? "Elevation data unavailable for this location" : ""}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold
                    border transition-all duration-200
                    ${disabled
                      ? "opacity-30 cursor-not-allowed border-white/10 text-slate-500"
                      : viewMode === "summit"
                      ? "bg-sky-500/20 border-sky-500/40 text-sky-300"
                      : "bg-white/5 border-white/10 text-slate-400 hover:border-white/20"
                    }`}
      >
        <span>{viewMode === "summit" ? "🏔" : "🏙"}</span>
        <span>{viewMode === "summit" ? "Summit" : "Standard"}</span>
        {isOverride && (
          <span className="text-slate-500 text-xs">·&nbsp;manual</span>
        )}
      </button>
    </div>
  );
}