import React, { useEffect } from "react";
import { Provider } from "react-redux";
import { useSelector } from "react-redux";
import store from "./store";
import AppLayout from "./layout/AppLayout";
import CurrentWeather from "./components/CurrentWeather";
import DailyForecast from "./components/DailyForecast";
import HourlyForecast from "./components/HourlyForecast";
import AirQualityCard from "./components/AirQualityCard";
import MarineCard from "./components/MarineCard";
import ClimateCard from "./components/ClimateCard";
import FeedbackButton from "./components/FeedbackButton";
import { ErrorState } from "./components/LoadingState";
import { useWeather } from "./hooks/useWeather";

const DEFAULT = { lat: 51.5074, lon: -0.1278, name: "London, GB" };

function WeatherDashboard() {
  const { forecastStatus, forecastError, aggregatedDaily, selectedDay, load } = useWeather();
  const marine       = useSelector((s) => s.weather.marine);
  const airQuality   = useSelector((s) => s.weather.airQuality);
  const climateNormals = useSelector((s) => s.weather.climateNormals);

  useEffect(() => {
    load(DEFAULT.lat, DEFAULT.lon, DEFAULT.name, 7);
  }, []);

  const isLoading = forecastStatus === "loading";
  const hasData   = aggregatedDaily.length > 0;

  return (
    <div className="space-y-6">
      {forecastStatus === "failed" && (
        <ErrorState
          message={forecastError || "Failed to load weather data"}
          onRetry={() => load(DEFAULT.lat, DEFAULT.lon, DEFAULT.name, 7)}
        />
      )}

      <CurrentWeather />

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
              {selectedDay
                ? `Hourly — ${new Date(selectedDay.date + "T12:00:00").toLocaleDateString([], {
                    weekday: "long", month: "short", day: "numeric",
                  })}`
                : "Hourly Breakdown"}
            </h2>
            <HourlyForecast />
          </section>
        </div>
      )}

      {hasData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {airQuality   && <AirQualityCard />}
          {marine       && <MarineCard />}
          {climateNormals && <ClimateCard />}
        </div>
      )}

      {!isLoading && !hasData && forecastStatus !== "failed" && (
        <div className="text-center py-20 space-y-3">
          <div className="text-6xl">🔍</div>
          <p className="text-slate-400 text-lg font-medium">Search for a location to get started</p>
          <p className="text-slate-600 text-sm">Try "Tokyo", "New York", or "Sydney"</p>
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

'''

**To view feedback**, visit:
https://weatherapp-backend-9c2l.onrender.com/api/feedback?secret=YOUR_SECRET

'''