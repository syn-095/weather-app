import React from "react";

const icons = {
  clear: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  ),
  "partly-cloudy": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="10" cy="10" r="3" />
      <path d="M10 3v1M10 17v-1M3 10h1M17 10h-1M5.22 5.22l.71.71M14.07 14.07l.71.71M5.22 14.78l.71-.71M14.07 5.93l.71-.71" />
      <path d="M11.5 13.5a4 4 0 1 1 0 5H8a3 3 0 0 1 0-6 3.5 3.5 0 0 1 3.5 1z" />
    </svg>
  ),
  cloudy: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z" />
    </svg>
  ),
  fog: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M3 10h18M3 14h18M5 18h14" />
      <path d="M17.5 7H9a5 5 0 0 1 0-2h8.5a3 3 0 0 1 0 6H8" />
    </svg>
  ),
  drizzle: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M17.5 14H9a5 5 0 0 1 0-2h8.5a3 3 0 0 1 0 6H8" />
      <path d="M8 19v2M12 19v2M16 19v2" />
    </svg>
  ),
  rain: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M17.5 12H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z" />
      <path d="M8 19l-2 3M12 19l-2 3M16 19l-2 3" />
    </svg>
  ),
  snow: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M17.5 12H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z" />
      <path d="M8 19l-1 2M12 19v2M16 19l1 2M7 21l2-1M11 21h2M15 21l2 1" />
    </svg>
  ),
  showers: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M17.5 12H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z" />
      <path d="M10 20v1M10 16v1M14 20v1M14 16v1" />
    </svg>
  ),
  thunder: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M17.5 12H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z" />
      <path d="M13 12l-4 8h6l-4 4" />
    </svg>
  ),
  unknown: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01" />
    </svg>
  ),
};

export default function WeatherIcon({ icon, className = "w-8 h-8" }) {
  return (
    <span className={className}>
      {icons[icon] || icons.unknown}
    </span>
  );
}