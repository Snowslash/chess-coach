import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ReadinessDashboard } from "./ReadinessDashboard";

describe("ReadinessDashboard", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads and renders Stockfish and Maia readiness with local privacy copy", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      if (String(input) === "/api/bootstrap") {
        return Promise.resolve(new Response(JSON.stringify({ app: { name: "Chess Coach", version: "1.0.0" }, privacy: { local_only: true, storage: "Generated reports stay local." } })));
      }
      return Promise.resolve(new Response(JSON.stringify({ stockfish: { status: "available", details: "Stockfish 16" }, maia: { status: "disabled", details: "Not enabled" } })));
    }));

    render(<ReadinessDashboard />);

    expect(screen.getByText("Checking local readiness…")).toBeInTheDocument();
    expect(await screen.findByText("Stockfish 16")).toBeInTheDocument();
    expect(screen.getByText("Not enabled")).toBeInTheDocument();
    expect(screen.getByText(/stay local/i)).toBeInTheDocument();
  });

  it("shows a recoverable error and retries both requests", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response("unavailable", { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ stockfish: { status: "missing", details: "No binary configured" }, maia: { status: "error", details: "Runtime unavailable" } })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ app: { name: "Chess Coach", version: "1.0.0" }, privacy: { local_only: true } })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ stockfish: { status: "missing", details: "No binary configured" }, maia: { status: "error", details: "Runtime unavailable" } })));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ReadinessDashboard />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Request failed (503).");
    await user.click(screen.getByRole("button", { name: "Retry readiness check" }));

    await waitFor(() => expect(screen.getByText("No binary configured")).toBeInTheDocument());
    expect(screen.getByText("Runtime unavailable")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });
});
