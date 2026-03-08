import { useState, useEffect } from "react";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000/api";
const PREF_KEY = "cairn_view_prefs";

function loadPrefs() {
  try { return JSON.parse(localStorage.getItem(PREF_KEY) || "{}"); }
  catch { return {}; }
}

function savePref(locationKey, mode) {
  const prefs = loadPrefs();
  prefs[locationKey] = mode;
  try { localStorage.setItem(PREF_KEY, JSON.stringify(prefs)); }
  catch {}
}

export function useElevation(lat, lon, locationName) {
  const [elevation, setElevation]   = useState(null);
  const [prominence, setProminence] = useState(null);
  const [viewMode, setViewMode]     = useState("standard"); // "standard" | "summit"
  const [autoMode, setAutoMode]     = useState("standard");
  const [loading, setLoading]       = useState(false);
  const [toggleDisabled, setToggleDisabled] = useState(false);

  const locationKey = locationName || `${lat},${lon}`;

  useEffect(() => {
    if (!lat || !lon) return;
    setLoading(true);

    fetch(`${API_BASE}/elevation?lat=${lat}&lon=${lon}`)
      .then(r => r.json())
      .then(data => {
        setElevation(data.elevation_m);
        setProminence(data.prominence_m);

        const suggested = data.suggest_summit_view ? "summit" : "standard";
        setAutoMode(suggested);

        // Check for saved user preference
        const prefs = loadPrefs();
        const saved = prefs[locationKey];
        if (saved) {
          setViewMode(saved);
        } else {
          setViewMode(suggested);
        }

        // Disable toggle if elevation data unavailable
        setToggleDisabled(data.elevation_m === null);
      })
      .catch(() => {
        setToggleDisabled(true);
        setViewMode("standard");
      })
      .finally(() => setLoading(false));
  }, [lat, lon, locationKey]);

  function toggleView() {
    const next = viewMode === "standard" ? "summit" : "standard";
    setViewMode(next);
    savePref(locationKey, next);
  }

  return {
    elevation,
    prominence,
    viewMode,       // current active mode
    autoMode,       // what the app suggested
    toggleView,
    toggleDisabled,
    isUserOverride: viewMode !== autoMode,
    loading,
  };
}