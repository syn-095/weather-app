import React, { useRef, useEffect } from "react";
import { useWeather, useDebounce } from "../hooks/useWeather";

export default function SearchBar() {
  const { searchQuery, searchResults, searchStatus, updateQuery, search, clearSearch, load } = useWeather();
  const inputRef = useRef(null);

  const debouncedSearch = useDebounce((q) => {
    if (q.trim().length >= 2) search(q);
  }, 400);

  const handleChange = (e) => {
    updateQuery(e.target.value);
    debouncedSearch(e.target.value);
  };

  const handleSelect = (r) => {
    load(r.latitude, r.longitude, `${r.name}, ${r.country}`, 7);
    clearSearch();
  };

  useEffect(() => {
    const handler = (e) => {
      if (!inputRef.current?.closest(".search-container")?.contains(e.target)) {
        clearSearch();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [clearSearch]);

  return (
    <div className="search-container relative w-full max-w-lg mx-auto">
      <div className="relative">
        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
        </span>
        <input
          ref={inputRef}
          type="text"
          value={searchQuery}
          onChange={handleChange}
          onKeyDown={(e) => e.key === "Escape" && clearSearch()}
          placeholder="Search city or location…"
          className="w-full pl-12 pr-4 py-3 rounded-2xl bg-white/10 backdrop-blur-md border border-white/20
                     text-white placeholder-slate-400 text-sm font-medium
                     focus:outline-none focus:ring-2 focus:ring-sky-400/50 transition-all duration-200"
          autoComplete="off"
        />
        {searchStatus === "loading" && (
          <span className="absolute right-4 top-1/2 -translate-y-1/2">
            <svg className="w-4 h-4 animate-spin text-sky-400" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </span>
        )}
      </div>

      {searchResults.length > 0 && (
        <ul className="absolute top-full mt-2 w-full z-50 rounded-2xl overflow-hidden
                       bg-slate-900/95 backdrop-blur-xl border border-white/10 shadow-2xl">
          {searchResults.map((r, i) => (
            <li key={i}>
              <button
                onClick={() => handleSelect(r)}
                className="w-full text-left px-4 py-3 hover:bg-white/10 transition-colors flex items-center gap-3"
              >
                <svg className="w-4 h-4 text-sky-400 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
                <span>
                  <span className="text-white text-sm font-medium">{r.name}</span>
                  {r.admin1 && <span className="text-slate-400 text-xs ml-1">{r.admin1},</span>}
                  <span className="text-slate-400 text-xs ml-1">{r.country}</span>
                </span>
                <span className="ml-auto text-slate-500 text-xs font-mono">
                  {r.latitude?.toFixed(2)}, {r.longitude?.toFixed(2)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}