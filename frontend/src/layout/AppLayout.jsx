import React from "react";
import SearchBar from "../components/SearchBar";
import { useWeather } from "../hooks/useWeather";

export default function AppLayout({ children }) {
  const { flipUnits, units } = useWeather();

  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 rounded-full bg-sky-900/20 blur-2xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full bg-blue-900/20 blur-2xl" />
      </div>

      <header className="relative z-20 border-b border-white/5 bg-slate-950/80 backdrop-blur-xl sticky top-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center gap-6">
          <div className="flex items-center gap-2.5 flex-shrink-0">
            <span className="text-2xl">🌤</span>
            <span className="font-black text-lg tracking-tight hidden sm:block">
              Cairn
            </span>
          </div>
          <div className="flex-1">
            <SearchBar />
          </div>
          <button
            onClick={flipUnits}
            className="flex-shrink-0 px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10
                       border border-white/10 text-sm font-semibold text-slate-300 transition-colors"
          >
            {units === "metric" ? "°C" : "°F"}
          </button>
        </div>
      </header>

      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      <footer className="relative z-10 border-t border-white/5 mt-12 py-6 text-center text-slate-600 text-xs">
        <p>Weather data from 7 providers · Cairn © {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}