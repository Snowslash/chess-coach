import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ResultsPage } from "./ResultsPage";

const analysisResult = {
  importedPgnPath: "input/lichess_recent_exampleuser.pgn",
  markdownPath: "reports/2026-07-09_exampleuser_recent.md",
  jsonPath: "reports/2026-07-09_exampleuser_recent.json",
  annotatedPgnPath: "reports/annotated/exampleuser_annotated.pgn",
  gamesAnalysed: 3,
  stdout: "runner stdout token=results-marker",
  stderr: "runner stderr authorization: Bearer results-marker",
};

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

describe("ResultsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    delete (window as Window & { chessCoachDesktop?: unknown }).chessCoachDesktop;
  });

  it("explains when no analysis result is available", () => {
    render(<ResultsPage result={null} />);

    expect(screen.getByRole("heading", { level: 2, name: "Results" })).toBeInTheDocument();
    expect(screen.getByText("No analysis result yet. Analyse games to prepare local outputs.")).toBeInTheDocument();
  });

  it("does not render native file buttons in browser mode", () => {
    render(<ResultsPage result={analysisResult} />);

    expect(screen.queryByRole("button", { name: "Open report" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open JSON" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open annotated PGN" })).not.toBeInTheDocument();
  });

  it("uses the latest project-relative analysis paths through the native bridge", async () => {
    const openPath = vi.fn().mockResolvedValue(undefined);
    Object.assign(window, { chessCoachDesktop: { openPath } });
    const user = userEvent.setup();
    const { rerender } = render(<ResultsPage result={analysisResult} />);
    const latestResult = {
      ...analysisResult,
      markdownPath: "reports/2026-07-10_exampleuser_recent.md",
      jsonPath: "reports/2026-07-10_exampleuser_recent.json",
      annotatedPgnPath: "reports/annotated/exampleuser_latest.pgn",
    };

    rerender(<ResultsPage result={latestResult} />);
    await user.click(screen.getByRole("button", { name: "Open report" }));
    await user.click(screen.getByRole("button", { name: "Open JSON" }));
    await user.click(screen.getByRole("button", { name: "Open annotated PGN" }));

    expect(openPath).toHaveBeenNthCalledWith(1, latestResult.markdownPath);
    expect(openPath).toHaveBeenNthCalledWith(2, latestResult.jsonPath);
    expect(openPath).toHaveBeenNthCalledWith(3, latestResult.annotatedPgnPath);
  });

  it("opens the latest result annotation path rather than an edited export destination", async () => {
    const openPath = vi.fn().mockResolvedValue(undefined);
    Object.assign(window, { chessCoachDesktop: { openPath } });
    const user = userEvent.setup();
    render(<ResultsPage result={analysisResult} />);

    await user.clear(screen.getByLabelText("Annotated PGN output path"));
    await user.type(screen.getByLabelText("Annotated PGN output path"), "reports/annotated/manual-export.pgn");
    await user.click(screen.getByRole("button", { name: "Open annotated PGN" }));

    expect(openPath).toHaveBeenCalledWith(analysisResult.annotatedPgnPath);
  });

  it("shows successful analysis metadata and exports annotated PGN from safe defaults", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ ok: true, out_path: "reports/annotated/exampleuser_annotated.pgn", games_exported: 2, stdout: "Annotated PGN created", stderr: "" }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<ResultsPage result={analysisResult} />);

    expect(screen.getByText("3 games analysed")).toBeInTheDocument();
    expect(screen.getByText("Imported PGN: input/lichess_recent_exampleuser.pgn")).toBeInTheDocument();
    expect(screen.getByLabelText("Analysis JSON source path")).toHaveValue(analysisResult.jsonPath);
    expect(screen.getByLabelText("Annotated PGN output path")).toHaveValue(analysisResult.annotatedPgnPath);
    expect(screen.getByText("Open generated files from the local project folder in browser mode.")).toBeInTheDocument();
    expect(screen.queryByText(/results-marker/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Export annotated PGN" }));

    expect(await screen.findByText("Exported 2 games to reports/annotated/exampleuser_annotated.pgn.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/export-annotated-pgn", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        json_path: analysisResult.jsonPath,
        out_path: analysisResult.annotatedPgnPath,
        max_games: 10,
        critical_only: true,
        include_all_moves: false,
      }),
    }));
  });

  it("keeps the latest analysis metadata visible when export fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: { errors: { json_path: "Analysis JSON was not found." } } }, 400)));
    const user = userEvent.setup();
    render(<ResultsPage result={analysisResult} />);

    await user.click(screen.getByRole("button", { name: "Export annotated PGN" }));

    const error = await screen.findByText("Annotated PGN export could not complete.");
    expect(error).toBeInTheDocument();
    expect(screen.getByText("3 games analysed")).toBeInTheDocument();
    expect(screen.getByText("Imported PGN: input/lichess_recent_exampleuser.pgn")).toBeInTheDocument();
    const source = screen.getByLabelText(/Analysis JSON source path/);
    expect(source).toHaveAttribute("aria-invalid", "true");
    expect(source).toHaveAttribute("aria-describedby", "json_path-error");
  });

  it("disables export controls while the synchronous export is running", async () => {
    let resolveExport: (value: Response) => void = () => undefined;
    const exportResponse = new Promise<Response>((resolve) => {
      resolveExport = resolve;
    });
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(exportResponse));
    const user = userEvent.setup();
    render(<ResultsPage result={analysisResult} />);

    await user.click(screen.getByRole("button", { name: "Export annotated PGN" }));

    expect(screen.getByRole("button", { name: "Exporting annotated PGN…" })).toBeDisabled();
    expect(screen.getByLabelText("Analysis JSON source path")).toBeDisabled();
    resolveExport(response({ ok: true, out_path: analysisResult.annotatedPgnPath, games_exported: 3, stdout: "", stderr: "" }));
    await waitFor(() => expect(screen.getByText("Exported 3 games to reports/annotated/exampleuser_annotated.pgn.")).toBeInTheDocument());
  });
});
