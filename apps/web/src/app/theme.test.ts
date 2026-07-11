import { afterEach, describe, expect, it } from "vitest";
import { applyTheme, getAppliedTheme, THEME_STORAGE_KEY } from "./theme";

describe("theme contract", () => {
  afterEach(() => {
    document.documentElement.classList.remove("dark");
    delete document.documentElement.dataset.theme;
    localStorage.clear();
  });

  it("applies and persists the shared dark theme", () => {
    expect(applyTheme("dark")).toBe("dark");
    expect(getAppliedTheme()).toBe("dark");
    expect(document.documentElement).toHaveClass("dark");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("returns to the shared light theme", () => {
    applyTheme("dark");
    applyTheme("light");
    expect(document.documentElement).not.toHaveClass("dark");
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});
