import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DiagnosticsPanel } from "./DiagnosticsPanel";

const result = {
  importedPgnPath: "input/lichess_recent_exampleuser.pgn",
  markdownPath: "reports/2026-07-09_exampleuser_recent.md",
  jsonPath: "reports/2026-07-09_exampleuser_recent.json",
  annotatedPgnPath: "reports/annotated/exampleuser_annotated.pgn",
  gamesAnalysed: 3,
  stdout: "runner stdout token=diagnostic-marker",
  stderr: "runner stderr authorization: Bearer diagnostic-marker",
};

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function diagnosticsFetch(diagnosticsResponse = response({ ok: true, path: ".coach/diagnostics/bundle-1" })) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    void init;
    if (String(input) === "/api/bootstrap") {
      return Promise.resolve(response({ app: { name: "Chess Coach", version: "1.0.0" }, privacy: { local_only: true, telemetry: false, storage: "Outputs stay local." } }));
    }
    if (String(input) === "/api/readiness") {
      return Promise.resolve(response({ stockfish: { status: "available", details: "Configured" }, maia: { status: "disabled", details: "Not enabled" } }));
    }
    return Promise.resolve(diagnosticsResponse);
  });
}

function diagnosticRequest(fetchMock: ReturnType<typeof diagnosticsFetch>) {
  return fetchMock.mock.calls.find(([input]) => input === "/api/diagnostics")?.[1]?.body;
}

describe("DiagnosticsPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads a concise local environment summary with private inclusion disabled by default", async () => {
    vi.stubGlobal("fetch", diagnosticsFetch());

    render(<DiagnosticsPanel recentMessages={[]} result={result} />);

    expect(await screen.findByRole("heading", { level: 2, name: "Diagnostics" })).toBeInTheDocument();
    expect(screen.getByText("Local-only: yes")).toBeInTheDocument();
    expect(screen.getByText("Stockfish: available — Configured")).toBeInTheDocument();
    expect(screen.getByLabelText("Include PGN in diagnostic bundle")).not.toBeChecked();
    expect(screen.getByLabelText("Include report in diagnostic bundle")).not.toBeChecked();
  });

  it("submits only explicitly included project-relative result paths and redacts token-shaped client messages", async () => {
    const fetchMock = diagnosticsFetch();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const syntheticGithubToken = ["ghp", "syntheticdiagnosticmarker"].join("_");
    const syntheticOpenAiKey = ["sk", "syntheticdiagnosticmarker"].join("-");
    const rawMarkers = [
      "token=diagnostic-marker-value",
      "authorization:*** Bearer authorization-marker-value",
      `GitHub ${syntheticGithubToken}`,
      `OpenAI ${syntheticOpenAiKey}`,
      "Personal 0123456789abcdef0123456789abcdef01234567",
    ];
    render(<DiagnosticsPanel recentMessages={rawMarkers} result={result} />);

    await screen.findByRole("heading", { level: 2, name: "Diagnostics" });
    for (const marker of ["diagnostic-marker-value", "authorization-marker-value", syntheticGithubToken, syntheticOpenAiKey, "0123456789abcdef0123456789abcdef01234567"]) {
      expect(screen.queryByText(new RegExp(marker))).not.toBeInTheDocument();
    }
    expect(screen.getByText("token=[redacted]")).toBeInTheDocument();
    expect(screen.getByText("authorization: [redacted]")).toBeInTheDocument();
    await user.click(screen.getByLabelText("Include PGN in diagnostic bundle"));
    await user.click(screen.getByLabelText("Include report in diagnostic bundle"));
    await user.click(screen.getByRole("button", { name: "Create diagnostic bundle" }));

    expect(await screen.findByText("Diagnostic bundle: .coach/diagnostics/bundle-1")).toBeInTheDocument();
    expect(diagnosticRequest(fetchMock)).toBe(JSON.stringify({
      include_pgn: true,
      include_report: true,
      selected_paths: {
        pgn: "input/lichess_recent_exampleuser.pgn",
        report: "reports/2026-07-09_exampleuser_recent.md",
      },
      recent_logs: [
        "token=[redacted]",
        "authorization: [redacted]",
        "GitHub [redacted]",
        "OpenAI [redacted]",
        "Personal [redacted]",
      ],
    }));
    for (const marker of rawMarkers) {
      expect(diagnosticRequest(fetchMock)).not.toContain(marker);
    }
  });

  it("does not display arbitrary absolute diagnostic bundle paths", async () => {
    vi.stubGlobal("fetch", diagnosticsFetch(response({ ok: true, path: "/srv/private/diagnostics/bundle-1.zip" })));
    const user = userEvent.setup();
    render(<DiagnosticsPanel recentMessages={[]} result={result} />);

    await screen.findByRole("heading", { level: 2, name: "Diagnostics" });
    await user.click(screen.getByRole("button", { name: "Create diagnostic bundle" }));

    expect(await screen.findByText("Diagnostic bundle created locally.")).toBeInTheDocument();
    expect(screen.queryByText(/\/srv\/private/)).not.toBeInTheDocument();
  });

  it("submits false inclusion flags when previously selected result paths disappear", async () => {
    const fetchMock = diagnosticsFetch();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const view = render(<DiagnosticsPanel recentMessages={["Analysed 3 games."]} result={result} />);

    await screen.findByRole("heading", { level: 2, name: "Diagnostics" });
    await user.click(screen.getByLabelText("Include PGN in diagnostic bundle"));
    await user.click(screen.getByLabelText("Include report in diagnostic bundle"));
    view.rerender(<DiagnosticsPanel recentMessages={["Analysed 3 games."]} result={null} />);
    await user.click(screen.getByRole("button", { name: "Create diagnostic bundle" }));

    expect(diagnosticRequest(fetchMock)).toBe(JSON.stringify({
      include_pgn: false,
      include_report: false,
      selected_paths: {},
      recent_logs: ["Analysed 3 games."],
    }));
  });

  it("keeps safe visible state when diagnostic creation fails", async () => {
    vi.stubGlobal("fetch", diagnosticsFetch(response({ detail: { errors: { selected_paths: "Path must stay inside the project." } } }, 400)));
    const user = userEvent.setup();
    render(<DiagnosticsPanel recentMessages={[]} result={result} />);

    await screen.findByRole("heading", { level: 2, name: "Diagnostics" });
    await user.click(screen.getByRole("button", { name: "Create diagnostic bundle" }));

    expect(await screen.findByText("Diagnostic bundle could not be created.")).toBeInTheDocument();
    expect(screen.getByText("Local-only: yes")).toBeInTheDocument();
  });
});
