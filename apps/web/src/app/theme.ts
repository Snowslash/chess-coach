export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "sangeevSiteTheme";

function normaliseTheme(value: string | null | undefined): Theme | null {
  return value === "dark" ? "dark" : value === "light" ? "light" : null;
}

function readStoredTheme(): Theme | null {
  try {
    return normaliseTheme(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch {
    return null;
  }
}

export function getAppliedTheme(): Theme {
  return normaliseTheme(document.documentElement.dataset.theme) ?? "light";
}

export function applyTheme(theme: Theme, persist = true): Theme {
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.classList.toggle("dark", theme === "dark");

  if (persist) {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Theme remains usable when storage is unavailable.
    }
  }

  return theme;
}

export function initialiseTheme(): Theme {
  const systemTheme: Theme = window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  return applyTheme(readStoredTheme() ?? systemTheme, false);
}
