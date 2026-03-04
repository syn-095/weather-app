import axios from "axios";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000/api";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
});

export async function fetchForecast(lat, lon, location = "", days = 7) {
  const { data } = await api.get("/weather/forecast", {
    params: { lat, lon, location, days },
  });
  if (data.error) throw new Error(data.error);
  return data;
}

export async function geocodeLocation(query) {
  const { data } = await api.get("/weather/geocode", { params: { q: query } });
  if (data.error) throw new Error(data.error);
  return data.results ?? [];
}

export async function healthCheck() {
  const { data } = await api.get("/health");
  return data;
}

export default api;