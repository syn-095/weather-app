import { useSelector, useDispatch } from "react-redux";
import { useCallback, useRef } from "react";
import {
  loadForecast,
  searchLocation,
  setSelectedDayIndex,
  toggleUnits,
  setSearchQuery,
  clearSearchResults,
  selectSelectedDay,
  selectHourlyForDay,
  toDisplayTemp,
  toDisplayWind,
  tempUnit,
  windUnit,
} from "../store/weatherSlice";

export function useWeather() {
  const dispatch = useDispatch();
  const weather = useSelector((s) => s.weather);
  const selectedDay = useSelector(selectSelectedDay);
  const hourlyForDay = useSelector(selectHourlyForDay);

  const load = useCallback(
    (lat, lon, location, days) => dispatch(loadForecast({ lat, lon, location, days })),
    [dispatch]
  );
  const search = useCallback((query) => dispatch(searchLocation(query)), [dispatch]);
  const selectDay = useCallback((index) => dispatch(setSelectedDayIndex(index)), [dispatch]);
  const flipUnits = useCallback(() => dispatch(toggleUnits()), [dispatch]);
  const updateQuery = useCallback((q) => dispatch(setSearchQuery(q)), [dispatch]);
  const clearSearch = useCallback(() => dispatch(clearSearchResults()), [dispatch]);

  const fmt = useCallback(
    (tempC) => toDisplayTemp(tempC, weather.units),
    [weather.units]
  );
  const fmtWind = useCallback(
    (kmh) => toDisplayWind(kmh, weather.units),
    [weather.units]
  );

  return {
    ...weather,
    selectedDay,
    hourlyForDay,
    tUnit: tempUnit(weather.units),
    wUnit: windUnit(weather.units),
    fmt,
    fmtWind,
    load,
    search,
    selectDay,
    flipUnits,
    updateQuery,
    clearSearch,
  };
}

export function useDebounce(callback, delay = 400) {
  const timer = useRef(null);
  return useCallback(
    (...args) => {
      clearTimeout(timer.current);
      timer.current = setTimeout(() => callback(...args), delay);
    },
    [callback, delay]
  );
}