import { configureStore } from "@reduxjs/toolkit";
import weatherReducer from "./weatherSlice";
import uiReducer from "./uiSlice";

export const store = configureStore({
  reducer: {
    weather: weatherReducer,
    ui: uiReducer,
  },
});

export default store;