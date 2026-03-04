import React from "react";

export function FullPageLoader() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4">
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 rounded-full border-2 border-sky-500/20" />
        <div className="absolute inset-0 rounded-full border-t-2 border-sky-400 animate-spin" />
      </div>
      <p className="text-slate-400 text-sm animate-pulse">Fetching weather data…</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="rounded-3xl p-8 bg-red-500/10 border border-red-500/20 text-center space-y-4">
      <div className="text-4xl">⚠️</div>
      <p className="text-red-300 font-medium">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 text-red-300 text-sm transition-colors border border-red-500/30"
        >
          Try again
        </button>
      )}
    </div>
  );
}