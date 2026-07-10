import { analysePgn, ApiError, createDiagnostics, exportAnnotatedPgn, getBootstrap, getConfig, getReadiness, importLichess, saveConfig, testLichess } from "./api";

describe("typed API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads bootstrap and readiness from same-origin API routes", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ app: { name: "Chess Coach", version: "1.0.0" }, privacy: { local_only: true } })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ stockfish: { status: "available", details: "Configured" }, maia: { status: "disabled", details: "Not enabled" } })));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getBootstrap()).resolves.toMatchObject({ app: { name: "Chess Coach" } });
    await expect(getReadiness()).resolves.toMatchObject({ stockfish: { status: "available" } });
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/bootstrap", expect.objectContaining({ signal: undefined }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/readiness", expect.objectContaining({ signal: undefined }));
  });

  it("returns a safe error for non-JSON failures without echoing a token-shaped response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("token=secret-token", { status: 500 })));

    await expect(getReadiness()).rejects.toMatchObject({
      message: "Request failed (500).",
      status: 500,
    });
  });

  it("unwraps allowlisted field errors from the FastAPI detail envelope", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: {
        errors: {
          default_player: "Use only letters, numbers, underscore or hyphen.",
          perf: "Choose rapid, blitz, bullet, or classical.",
          unexpected_field: "Do not surface this arbitrary error.",
        },
      },
    }), { status: 400 })));

    try {
      await saveConfig({ default_player: "bad name!", lichess_token: "", stockfish_path: "", stockfish_depth: 12, stockfish_time_limit: 0.5, maia2_enabled: false, maia2_game_type: "rapid", maia2_device: "cpu", maia2_target_elo: 1500, default_pgn: "input/example.pgn", default_out: "reports/example.md" });
      expect.unreachable("saveConfig should reject a validation response");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).errors).toEqual({
        default_player: "Use only letters, numbers, underscore or hyphen.",
        perf: "Choose rapid, blitz, bullet, or classical.",
      });
    }
  });

  it("uses typed config and Lichess requests without reading a configured token", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ exists: true, config: { default_player: "ExampleUser", lichess_token: "" }, lichess_token_configured: true, validation: { ok: true, errors: {}, warnings: {} }, options: {} })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, config: { default_player: "ExampleUser", lichess_token: "" }, lichess_token_configured: true, validation: { ok: true, errors: {}, warnings: {} } })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, status: "available", message: "Found ExampleUser" })));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getConfig()).resolves.toMatchObject({ lichess_token_configured: true, config: { lichess_token: "" } });
    await expect(saveConfig({ default_player: "ExampleUser", lichess_token: "", stockfish_path: "", stockfish_depth: 12, stockfish_time_limit: 0.5, maia2_enabled: false, maia2_game_type: "rapid", maia2_device: "cpu", maia2_target_elo: 1500, default_pgn: "input/example.pgn", default_out: "reports/example.md" })).resolves.toMatchObject({ ok: true });
    await expect(testLichess({ username: "ExampleUser", token: "" })).resolves.toMatchObject({ status: "available" });

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/config", expect.objectContaining({ method: "GET" }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/config", expect.objectContaining({ method: "POST" }));
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/lichess/test", expect.objectContaining({ method: "POST" }));
    expect(fetchMock.mock.calls[1][1]?.body).not.toContain("configured-token");
  });

  it("sends typed Lichess check, import, and analysis requests to same-origin API routes", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, status: "available", message: "Found ExampleUser" })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, out_path: "input/lichess_recent_exampleuser.pgn", stdout: "Imported", stderr: "" })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, markdown_path: "reports/2026-07-09_exampleuser_recent.md", json_path: "reports/2026-07-09_exampleuser_recent.json", games_analysed: 4, stdout: "Analysed", stderr: "" })));
    vi.stubGlobal("fetch", fetchMock);

    await testLichess({ username: "ExampleUser", token: "" });
    await importLichess({ username: "ExampleUser", max_games: 12, perf: "rapid", rated_only: true, since_days: 7, out_path: "input/lichess_recent_exampleuser.pgn" });
    await analysePgn({ username: "ExampleUser", pgn_path: "input/lichess_recent_exampleuser.pgn", out_path: "reports/2026-07-09_exampleuser_recent.md", mock: false });

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/lichess/test", expect.objectContaining({ method: "POST", body: JSON.stringify({ username: "ExampleUser", token: "" }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/import-lichess", expect.objectContaining({ method: "POST", body: JSON.stringify({ username: "ExampleUser", max_games: 12, perf: "rapid", rated_only: true, since_days: 7, out_path: "input/lichess_recent_exampleuser.pgn" }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/analyse", expect.objectContaining({ method: "POST", body: JSON.stringify({ username: "ExampleUser", pgn_path: "input/lichess_recent_exampleuser.pgn", out_path: "reports/2026-07-09_exampleuser_recent.md", mock: false }) }));
  });

  it("sends typed export and diagnostics requests with explicit local inputs", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, out_path: "reports/annotated/exampleuser_annotated.pgn", games_exported: 2, stdout: "Exported", stderr: "" })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true, path: ".coach/diagnostics/bundle-1" })));
    vi.stubGlobal("fetch", fetchMock);

    await exportAnnotatedPgn({ json_path: "reports/2026-07-09_exampleuser_recent.json", out_path: "reports/annotated/exampleuser_annotated.pgn", max_games: 10, critical_only: true, include_all_moves: false });
    await createDiagnostics({ include_pgn: false, include_report: false, selected_paths: {}, recent_logs: ["Analysis complete"] });

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/export-annotated-pgn", expect.objectContaining({ method: "POST", body: JSON.stringify({ json_path: "reports/2026-07-09_exampleuser_recent.json", out_path: "reports/annotated/exampleuser_annotated.pgn", max_games: 10, critical_only: true, include_all_moves: false }) }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/diagnostics", expect.objectContaining({ method: "POST", body: JSON.stringify({ include_pgn: false, include_report: false, selected_paths: {}, recent_logs: ["Analysis complete"] }) }));
  });
});
