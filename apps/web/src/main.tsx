import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { initialiseTheme } from "./app/theme";
import "./styles/globals.css";

initialiseTheme();
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
