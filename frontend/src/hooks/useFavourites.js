const KEY = "cairn_favourites";
const MAX = 5;

function read() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(favs) {
  try {
    localStorage.setItem(KEY, JSON.stringify(favs));
  } catch {}
}

import { useState, useCallback } from "react";

export function useFavourites() {
  const [favourites, setFavourites] = useState(() => read());

  const isFavourite = useCallback(
    (lat, lon) =>
      favourites.some(
        (f) => Math.abs(f.lat - lat) < 0.001 && Math.abs(f.lon - lon) < 0.001
      ),
    [favourites]
  );

  const addFavourite = useCallback((lat, lon, name) => {
    setFavourites((prev) => {
      if (prev.some((f) => Math.abs(f.lat - lat) < 0.001 && Math.abs(f.lon - lon) < 0.001))
        return prev;
      if (prev.length >= MAX) return prev;
      const next = [...prev, { lat, lon, name }];
      write(next);
      return next;
    });
  }, []);

  const removeFavourite = useCallback((lat, lon) => {
    setFavourites((prev) => {
      const next = prev.filter(
        (f) => !(Math.abs(f.lat - lat) < 0.001 && Math.abs(f.lon - lon) < 0.001)
      );
      write(next);
      return next;
    });
  }, []);

  const toggleFavourite = useCallback(
    (lat, lon, name) => {
      if (isFavourite(lat, lon)) removeFavourite(lat, lon);
      else addFavourite(lat, lon, name);
    },
    [isFavourite, addFavourite, removeFavourite]
  );

  return { favourites, isFavourite, toggleFavourite, maxReached: favourites.length >= MAX };
}