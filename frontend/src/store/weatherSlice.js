import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { fetchForecast, geocodeLocation } from "../services/weatherApi";

export const searchLocation = createAsyncThunk(
  "weather/searchLocation",
  async (query, { rejectWithValue }) => {
    try {
      return await geocodeLocation(query);
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const loadForecast = createAsyncThunk(
  "weather/loadForecast",
  async ({ lat, lon, location, days = 7 }, { rejectWithValue }) => {
    try {
      return await fetchForecast(lat, lon, location, days);
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

const weatherSlice = createSlice({
  name: "weather",
  initialState: {
    current: null,
    aggregatedDaily: [],
    sources: [],
    location: "",
    latitude: null,
    longitude: null,
    fetchedAt: null,
    airQuality: null,
    marine: null,
    climateNormals: null,
    searchResults: [],
    searchQuery: "",
    selectedDayIndex: 0,
    units: "metric",
    forecastStatus: "idle",
    searchStatus: "idle",
    forecastError: null,
    searchError: null,
  },
  reducers: {
    setSelectedDayIndex(state, action) {
      state.selectedDayIndex = action.payload;
    },
    toggleUnits(state) {
      state.units = state.units === "metric" ? "imperial" : "metric";
    },
    setSearchQuery(state, action) {
      state.searchQuery = action.payload;
      if (!action.payload) state.searchResults = [];
    },
    clearSearchResults(state) {
      state.searchResults = [];
      state.searchQuery = "";
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadForecast.pending, (state) => {
        state.forecastStatus = "loading";
        state.forecastError = null;
      })
      .addCase(loadForecast.fulfilled, (state, action) => {
        state.forecastStatus = "succeeded";
        state.current = action.payload.current;
        state.aggregatedDaily = action.payload.aggregated_daily;
        state.sources = action.payload.sources;
        state.location = action.payload.location;
        state.latitude = action.payload.latitude;
        state.longitude = action.payload.longitude;
        state.fetchedAt = action.payload.fetched_at;
        state.airQuality = action.payload.air_quality ?? null;
        state.marine = action.payload.marine ?? null;
        state.climateNormals = action.payload.climate_normals ?? null;
        state.selectedDayIndex = 0;
      })
      .addCase(loadForecast.rejected, (state, action) => {
        state.forecastStatus = "failed";
        state.forecastError = action.payload;
      })
      .addCase(searchLocation.pending, (state) => {
        state.searchStatus = "loading";
        state.searchError = null;
      })
      .addCase(searchLocation.fulfilled, (state, action) => {
        state.searchStatus = "succeeded";
        state.searchResults = action.payload;
      })
      .addCase(searchLocation.rejected, (state, action) => {
        state.searchStatus = "failed";
        state.searchError = action.payload;
      });
  },
});

export const { setSelectedDayIndex, toggleUnits, setSearchQuery, clearSearchResults } =
  weatherSlice.actions;

export const selectSelectedDay = (state) =>
  state.weather.aggregatedDaily[state.weather.selectedDayIndex] ?? null;

export const selectHourlyForDay = (state) =>
  selectSelectedDay(state)?.hourly ?? [];

export const toDisplayTemp = (tempC, units) =>
  units === "imperial" ? Math.round((tempC * 9) / 5 + 32) : Math.round(tempC * 10) / 10;

export const toDisplayWind = (kmh, units) =>
  units === "imperial" ? Math.round(kmh * 0.621371) : Math.round(kmh);

export const tempUnit = (units) => (units === "imperial" ? "°F" : "°C");
export const windUnit = (units) => (units === "imperial" ? "mph" : "km/h");

export default weatherSlice.reducer;