import React, { useEffect } from "react";
import { Provider, useSelector } from "react-redux";
import store from "./store";
import AppLayout from "./layout/AppLayout";
import CurrentWeather from "./components/CurrentWeather";
import DailyForecast from "./components/DailyForecast";
import HourlyForecast from "./components/HourlyForecast";
import AirQualityCard from "./components/AirQualityCard";
import MarineCard from "./components/MarineCard";
import ClimateCard from "./components/ClimateCard";
import FeedbackButton from "./components/FeedbackButton";
import GroundTruthCard from "./components/GroundTruthCard";
import ViewToggle from "./components/ViewToggle";
import { ErrorState } from "./components/LoadingState";
import { useWeather } from "./hooks/useWeather";
import { useElevation } from "./hooks/useElevation";

const DEFAULT     = { lat: 51.5074, lon: -0.1278, name: "London, GB" };
const API_BASE    = process.env.REACT_APP_API_URL || "http://localhost:5000/api";
const LOCATION_KEY = "cairn_last_location";

function getInitialLocation() {
  try {
    const saved = localStorage.getItem(LOCATION_KEY);
    if (saved) {
      const p = JSON.parse(saved);
      if (p.lat && p.lon && p.name) return p;
    }
  } catch {}
  return DEFAULT;
}

function saveLocation(lat, lon, name) {
  try {
    localStorage.setItem(LOCATION_KEY, JSON.stringify({ lat, lon, name }));
  } catch {}
}

function pingAnalytics(locationName) {
  fetch(`${API_BASE}/analytics/pageview`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ location: locationName }),
  }).catch(() => {});
}

function formatDayTitle(selectedDay) {
  if (!selectedDay) return "Hourly Breakdown";
  return "Hourly \u2014 " + new Date(selectedDay.date + "T12:00:00")
    .toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" });
}

function WeatherDashboard() {
  const {
    forecastStatus, forecastError,
    aggregatedDaily, selectedDay, load,
  } = useWeather();

  const marine         = useSelector((s) => s.weather.marine);
  const airQuality     = useSelector((s) => s.weather.airQuality);
  const climateNormals = useSelector((s) => s.weather.climateNormals);
  const currentLocation = useSelector((s) => s.weather.location);
  const latitude        = useSelector((s) => s.weather.latitude);
  const longitude       = useSelector((s) => s.weather.longitude);

  const {
    elevation, viewMode, autoMode,
    toggleView, toggleDisabled, isUserOverride,
  } = useElevation(latitude, longitude, currentLocation);

  useEffect(() => {
    const initial = getInitialLocation();
    load(initial.lat, initial.lon, initial.name, 7);
    pingAnalytics(initial.name);
  }, []);

  useEffect(() => {
    if (currentLocation && latitude && longitude) {
      saveLocation(latitude, longitude, currentLocation);
    }
  }, [currentLocation, latitude, longitude]);

  const isLoading = forecastStatus === "loading";
  const hasData   = aggregatedDaily.length > 0;
  const isSummit  = viewMode === "summit";

  return (
    <div className="space-y-6">
      {forecastStatus === "failed" && (
        <ErrorState
          message={forecastError || "Failed to load weather data"}
          onRetry={() => { const l = getInitialLocation(); load(l.lat, l.lon, l.name, 7); }}
        />
      )}

      {/* View toggle — sits above hero card */}
      {hasData && (
        <div className="flex justify-end px-1">
          <ViewToggle
            viewMode={viewMode}
            onToggle={toggleView}
            disabled={toggleDisabled}
            isOverride={isUserOverride}
            elevation={elevation}
          />
        </div>
      )}

      <CurrentWeather summitMode={isSummit} />

      {(isLoading || hasData) && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <section className="rounded-3xl p-5 bg-white/5 border border-white/10 backdrop-blur-sm">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">
              7-Day Forecast
            </h2>
            <DailyForecast />
          </section>
          <section className="rounded-3xl p-5 bg-white/5 border border-white/10 backdrop-blur-sm">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">
              {formatDayTitle(selectedDay)}
            </h2>
            <HourlyForecast />
          </section>
        </div>
      )}

      {hasData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {airQuality    && <AirQualityCard />}
          {marine        && <MarineCard />}
          {climateNormals && <ClimateCard />}
        </div>
      )}

      {/* Ground truth — always show when data loaded */}
      {hasData && <GroundTruthCard />}

      {!isLoading && !hasData && forecastStatus !== "failed" && (
        <div className="text-center py-20 space-y-3">
          <div className="text-6xl">🏔</div>
          <p className="text-slate-400 text-lg font-medium">Search for a location to get started</p>
          <p className="text-slate-600 text-sm">Try "Ben Nevis", "Chamonix", or "London"</p>
        </div>
      )}
    </div>
  );
}

export default function App() {
  return (
    <Provider store={store}>
      <AppLayout>
        <WeatherDashboard />
        <FeedbackButton />
      </AppLayout>
    </Provider>
  );
}