import React from "react";

export default function FavouritesBar({ favourites, currentLat, currentLon, onSelect, onRemove }) {
  if (favourites.length === 0) return null;

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-xs text-slate-500 uppercase tracking-wider shrink-0">Saved</span>
      {favourites.map((fav) => {
        const isActive =
          Math.abs(fav.lat - currentLat) < 0.001 &&
          Math.abs(fav.lon - currentLon) < 0.001;
        return (
          <div
            key={`${fav.lat},${fav.lon}`}
            className={`group flex items-center gap-1.5 pl-3 pr-1.5 py-1.5 rounded-full
                        border text-xs font-medium transition-all cursor-pointer
                        ${isActive
                          ? "bg-sky-500/20 border-sky-400/40 text-sky-300"
                          : "bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 hover:border-white/20"
                        }`}
          >
            <span onClick={() => onSelect(fav)} className="truncate max-w-[120px]">
              {fav.name.split(",")[0]}
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); onRemove(fav.lat, fav.lon); }}
              className={`rounded-full p-0.5 transition-colors
                          ${isActive
                            ? "text-sky-400 hover:text-white hover:bg-sky-500/30"
                            : "text-slate-600 hover:text-slate-300 hover:bg-white/10"
                          }`}
              title="Remove"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M18 6 6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>
        );
      })}
    </div>
  );
}