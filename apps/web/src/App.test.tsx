import { render, screen } from "@testing-library/react";

import { App } from "./App";

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the Chess Coach shell with local privacy copy and primary navigation", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(() => undefined)));

    render(<App />);

    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Chess Coach" })).toBeInTheDocument();
    expect(screen.getByText(/runs locally/i)).toBeInTheDocument();
    const navigation = screen.getByRole("navigation", { name: "Primary" });
    for (const label of ["Home", "Analyse", "Results", "Diagnostics", "Settings / Advanced"]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(navigation).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Analyse games" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Results" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Diagnostics" })).toBeInTheDocument();
  });
});
