import { createSlice } from "@reduxjs/toolkit";

const uiSlice = createSlice({
  name: "ui",
  initialState: {
    theme: "dark",
    sidebarOpen: false,
  },
  reducers: {
    toggleTheme(state) {
      state.theme = state.theme === "dark" ? "light" : "dark";
    },
    setSidebarOpen(state, action) {
      state.sidebarOpen = action.payload;
    },
  },
});

export const { toggleTheme, setSidebarOpen } = uiSlice.actions;
export default uiSlice.reducer;