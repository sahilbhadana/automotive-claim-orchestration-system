import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

// Apply the saved theme before first paint to avoid a flash of wrong theme.
document.documentElement.dataset.theme =
  localStorage.getItem("claimflow_theme") ?? "dark";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
