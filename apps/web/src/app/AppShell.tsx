import { useState, type PropsWithChildren } from "react";

import { Button } from "@/components/ui/button";
import { applyTheme, getAppliedTheme, type Theme } from "./theme";

export function AppShell({ children }: PropsWithChildren) {
  const [theme, setTheme] = useState<Theme>(getAppliedTheme);

  return (
    <div className="app-shell">
      <header className="site-header">
        <div>
          <h1>Chess Coach</h1>
          <p className="header-privacy">Runs locally. No hosted service, analytics or telemetry.</p>
        </div>
        <Button
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          className="theme-toggle button--secondary"
          onClick={() => {
            const nextTheme: Theme = theme === "dark" ? "light" : "dark";
            setTheme(applyTheme(nextTheme));
          }}
        >
          {theme === "dark" ? "Light" : "Dark"}
        </Button>
      </header>
      <nav aria-label="Primary" className="primary-nav">
        <a aria-current="page" href="#home">Home</a>
        <a href="#analyse">Analyse</a>
        <a href="#results">Results</a>
        <a href="#diagnostics">Diagnostics</a>
        <a href="#settings" onClick={() => document.querySelector<HTMLDetailsElement>("#settings details")?.setAttribute("open", "")}>Settings / Advanced</a>
      </nav>
      <main id="home">{children}</main>
    </div>
  );
}
