import { useState } from "react";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { WorkflowSection } from "./WorkflowSection";
import type { WorkflowResult } from "./workflow-result";

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

describe("WorkflowSection", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses labelled project-relative paths, safe recommendations, and an accessible source group", async () => {
    const user = userEvent.setup();
    render(<WorkflowSection today={() => "2026-07-09"} />);

    expect(screen.getByText("Enter a valid Lichess username to see safe workflow path suggestions.")).toBeInTheDocument();
    expect(screen.getByLabelText("PGN path")).toHaveValue("");
    expect(screen.getByRole("radiogroup", { name: "Game source" })).toBeInTheDocument();
    expect(screen.getByLabelText("Import recent public Lichess games")).toBeChecked();
    expect(screen.getByLabelText("Rated games only")).toBeChecked();
    expect(screen.getByLabelText("Performance filter").tagName).toBe("SELECT");
    expect(screen.getByLabelText("Performance filter")).toHaveValue("");

    await user.type(screen.getByLabelText("Lichess username"), "ExampleUser");

    expect(screen.getByLabelText("PGN path")).toHaveValue("input/lichess_recent_exampleuser.pgn");
    expect(screen.getByLabelText("Markdown report output path")).toHaveValue("reports/2026-07-09_exampleuser_recent.md");
    expect(screen.getByText("Browser mode accepts project-relative paths only.")).toBeInTheDocument();
  });

  it("preserves manual path overrides until Reset suggested paths is selected", async () => {
    const user = userEvent.setup();
    render(<WorkflowSection today={() => "2026-07-09"} />);
    const username = screen.getByLabelText("Lichess username");
    const markdown = screen.getByLabelText("Markdown report output path");

    await user.type(username, "ExampleUser");
    await user.clear(markdown);
    await user.type(markdown, "reports/custom.md");
    await user.clear(username);
    await user.type(username, "OtherUser");

    expect(markdown).toHaveValue("reports/custom.md");
    expect(screen.getByLabelText("PGN path")).toHaveValue("input/lichess_recent_otheruser.pgn");

    await user.click(screen.getByRole("button", { name: "Reset suggested paths" }));

    expect(markdown).toHaveValue("reports/2026-07-09_otheruser_recent.md");
  });

  it("allows import-only with a valid import PGN path when no Markdown report path is set", async () => {
    const user = userEvent.setup();
    render(<WorkflowSection today={() => "2026-07-09"} />);

    await user.type(screen.getByLabelText("Lichess username"), "ExampleUser");
    await user.clear(screen.getByLabelText("Markdown report output path"));

    expect(screen.getByRole("button", { name: "Import games" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Import and analyse games" })).toBeDisabled();
  });

  it("checks Lichess with a blank token then imports, analyses, and lifts the result", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ ok: true, status: "available", message: "Public games available" }))
      .mockResolvedValueOnce(response({ ok: true, out_path: "input/lichess_recent_exampleuser.pgn", stdout: "Imported games", stderr: "" }))
      .mockResolvedValueOnce(response({ ok: true, markdown_path: "reports/2026-07-09_exampleuser_recent.md", json_path: "reports/2026-07-09_exampleuser_recent.json", games_analysed: 3, stdout: "Analysis complete", stderr: "" }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const onResult = vi.fn();
    render(<WorkflowSection onResult={onResult} today={() => "2026-07-09"} />);

    await user.type(screen.getByLabelText("Lichess username"), "ExampleUser");
    await user.click(screen.getByRole("button", { name: "Test Lichess access" }));
    expect(await screen.findByText("Public games available")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Import and analyse games" }));

    expect(await screen.findByText("Analysed 3 games. Review the Results section for local outputs.")).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][1]?.body).toBe(JSON.stringify({ username: "ExampleUser", token: "" }));
    expect(fetchMock.mock.calls[1][0]).toBe("/api/import-lichess");
    expect(fetchMock.mock.calls[1][1]?.body).toBe(JSON.stringify({ username: "ExampleUser", max_games: 20, perf: null, rated_only: true, since_days: null, out_path: "input/lichess_recent_exampleuser.pgn" }));
    expect(fetchMock.mock.calls[2][0]).toBe("/api/analyse");
    expect(onResult).toHaveBeenCalledWith(expect.objectContaining({
      importedPgnPath: "input/lichess_recent_exampleuser.pgn",
      jsonPath: "reports/2026-07-09_exampleuser_recent.json",
      annotatedPgnPath: "reports/annotated/exampleuser_annotated.pgn",
      gamesAnalysed: 3,
    }));
  });

  it("analyses an existing project-relative PGN without importing", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ ok: true, markdown_path: "reports/2026-07-09_exampleuser_recent.md", json_path: "reports/2026-07-09_exampleuser_recent.json", games_analysed: 1, stdout: "Analysis complete", stderr: "" }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<WorkflowSection today={() => "2026-07-09"} />);

    await user.type(screen.getByLabelText("Lichess username"), "ExampleUser");
    await user.click(screen.getByLabelText("Analyse an existing project-relative PGN"));
    const pgn = screen.getByLabelText("PGN path");
    await user.clear(pgn);
    await user.type(pgn, "input/recent.pgn");
    await user.click(screen.getByRole("button", { name: "Analyse existing PGN" }));

    await screen.findByText("Analysed 1 game. Review the Results section for local outputs.");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/analyse");
    expect(fetchMock.mock.calls[0][1]?.body).toContain("input/recent.pgn");
  });

  it("imports games without analysing or replacing an earlier lifted result", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ ok: true, out_path: "input/lichess_recent_exampleuser.pgn", stdout: "", stderr: "" }))
      .mockResolvedValueOnce(response({ ok: true, markdown_path: "reports/2026-07-09_exampleuser_recent.md", json_path: "reports/2026-07-09_exampleuser_recent.json", games_analysed: 3, stdout: "", stderr: "" }))
      .mockResolvedValueOnce(response({ ok: true, out_path: "input/lichess_recent_exampleuser.pgn", stdout: "", stderr: "" }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    function WorkflowWithResult() {
      const [result, setResult] = useState<WorkflowResult | null>(null);
      return <><WorkflowSection onResult={setResult} today={() => "2026-07-09"} /><p>Result: {result?.markdownPath ?? "none"}</p></>;
    }
    render(<WorkflowWithResult />);

    await user.type(screen.getByLabelText("Lichess username"), "ExampleUser");
    await user.click(screen.getByRole("button", { name: "Import and analyse games" }));
    expect(await screen.findByText("Result: reports/2026-07-09_exampleuser_recent.md")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Import games" }));

    expect(await screen.findByText("Imported games to input/lichess_recent_exampleuser.pgn. Analyse them from the existing PGN source when ready.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[2][0]).toBe("/api/import-lichess");
    expect(screen.getByText("Result: reports/2026-07-09_exampleuser_recent.md")).toBeInTheDocument();
  });

  it("disables conflicting controls while importing and reports safe field errors", async () => {
    let resolveImport: (value: Response) => void = () => undefined;
    const importResponse = new Promise<Response>((resolve) => {
      resolveImport = resolve;
    });
    const fetchMock = vi.fn()
      .mockReturnValueOnce(importResponse)
      .mockResolvedValueOnce(response({ ok: true, markdown_path: "reports/2026-07-09_exampleuser_recent.md", json_path: "reports/2026-07-09_exampleuser_recent.json", games_analysed: 1, stdout: "", stderr: "" }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<WorkflowSection today={() => "2026-07-09"} />);

    await user.type(screen.getByLabelText("Lichess username"), "ExampleUser");
    await user.click(screen.getByRole("button", { name: "Import and analyse games" }));

    expect(screen.getByRole("button", { name: "Import and analyse games" })).toBeDisabled();
    expect(screen.getByLabelText("Analyse an existing project-relative PGN")).toBeDisabled();
    resolveImport(response({ ok: false, out_path: "", stdout: "", stderr: "" }, 400));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Import and analysis could not complete."));
  });
});
