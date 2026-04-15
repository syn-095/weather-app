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
import FavouritesBar from "./components/FavouritesBar";
import { ErrorState } from "./components/LoadingState";
import { useWeather } from "./hooks/useWeather";
import { useElevation } from "./hooks/useElevation";
import { useFavourites } from "./hooks/useFavourites";

const DEFAULT      = { lat: 51.5074, lon: -0.1278, name: "London, GB" };
const API_BASE     = process.env.REACT_APP_API_URL || "http://localhost:5000/api";
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
  return "Hourly — " + new Date(selectedDay.date + "T12:00:00")
    .toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" });
}

function StarButton({ isFav, disabled, onToggle }) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      title={isFav ? "Remove from favourites" : disabled ? "Max 5 favourites" : "Save to favourites"}
      className={`p-1.5 rounded-full transition-all
                  ${isFav
                    ? "text-yellow-400 hover:text-yellow-300"
                    : disabled
                      ? "text-slate-700 cursor-not-allowed"
                      : "text-slate-500 hover:text-yellow-400"
                  }`}
    >
      <svg className="w-5 h-5" fill={isFav ? "currentColor" : "none"}
           stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
      </svg>
    </button>
  );
}

function WeatherDashboard() {
  const {
    forecastStatus, forecastError,
    aggregatedDaily, selectedDay, load,
  } = useWeather();

  const marine          = useSelector((s) => s.weather.marine);
  const airQuality      = useSelector((s) => s.weather.airQuality);
  const climateNormals  = useSelector((s) => s.weather.climateNormals);
  const currentLocation = useSelector((s) => s.weather.location);
  const latitude        = useSelector((s) => s.weather.latitude);
  const longitude       = useSelector((s) => s.weather.longitude);

  const {
    elevation, viewMode, autoMode,
    toggleView, toggleDisabled, isUserOverride,
  } = useElevation(latitude, longitude, currentLocation);

  const { favourites, isFavourite, toggleFavourite, maxReached } = useFavourites();

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
  const currentIsFav = latitude && longitude ? isFavourite(latitude, longitude) : false;

  function handleSelectFavourite(fav) {
    load(fav.lat, fav.lon, fav.name, 7);
    pingAnalytics(fav.name);
  }

  function handleRemoveFavourite(lat, lon) {
    toggleFavourite(lat, lon, "");
  }

  return (
    <div className="space-y-6">
      {forecastStatus === "failed" && (
        <ErrorState
          message={forecastError || "Failed to load weather data"}
          onRetry={() => { const l = getInitialLocation(); load(l.lat, l.lon, l.name, 7); }}
        />
      )}

      {/* Favourites bar */}
      {favourites.length > 0 && (
        <FavouritesBar
          favourites={favourites}
          currentLat={latitude}
          currentLon={longitude}
          onSelect={handleSelectFavourite}
          onRemove={handleRemoveFavourite}
        />
      )}

      {/* View toggle + star button */}
      {hasData && (
        <div className="flex items-center justify-between px-1">
          <StarButton
            isFav={currentIsFav}
            disabled={!currentIsFav && maxReached}
            onToggle={() => latitude && longitude && toggleFavourite(latitude, longitude, currentLocation)}
          />
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
          <section className="rounded-3xl p-5 bg-white/5 border border-white/10">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">
              7-Day Forecast
            </h2>
            <DailyForecast />
          </section>
          <section className="rounded-3xl p-5 bg-white/5 border border-white/10">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">
              {formatDayTitle(selectedDay)}
            </h2>
            <HourlyForecast />
          </section>
        </div>
      )}

      {hasData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {airQuality     && <AirQualityCard />}
          {marine         && <MarineCard />}
          {climateNormals && <ClimateCard />}
        </div>
      )}

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