import { analysePgn } from "./api";

afterEach(() => vi.unstubAllGlobals());

it("bootstraps a fresh session header for mutations without persistence", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ session_token: "SYNTHETIC-session" })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true })));
  vi.stubGlobal("fetch", fetchMock);
  await analysePgn({ username: "ExampleUser", pgn_path: "input/sample_games.pgn", out_path: "reports/example.md", mock: false });
  expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/bootstrap", expect.anything());
  expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/analyse", expect.objectContaining({
    headers: { "Content-Type": "application/json", "X-Chess-Coach-Session": "SYNTHETIC-session" },
  }));
  expect(localStorage.length).toBe(0);
});

it("does not mutate when bootstrap supplies no token", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response("{}"));
  vi.stubGlobal("fetch", fetchMock);
  await expect(analysePgn({ username: "ExampleUser", pgn_path: "input/sample_games.pgn", out_path: "reports/example.md", mock: false })).rejects.toThrow("Local session unavailable.");
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
