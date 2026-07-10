import { expect, test } from "@playwright/test";

const configResponse = {
  exists: false,
  config: {
    default_player: "",
    lichess_token: "",
    stockfish_path: "",
    stockfish_depth: 12,
    stockfish_time_limit: 0.5,
    maia2_enabled: false,
    maia2_game_type: "rapid",
    maia2_device: "cpu",
    maia2_target_elo: 1500,
    default_pgn: "input/sample_games.pgn",
    default_out: "reports/latest.md",
  },
  lichess_token_configured: true,
  validation: { ok: true, errors: {}, warnings: {} },
  options: { maia_game_types: ["rapid"], maia_devices: ["cpu"], maia_elo: [1500] },
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/config", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(configResponse) });
  });
});

test("built FastAPI root renders required sections and remains responsive", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1, name: "Chess Coach" })).toBeVisible();
  await expect(page.getByText(/Runs locally/)).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Local readiness" })).toBeVisible();
  for (const heading of ["Analyse games", "Results", "Diagnostics", "Settings"]) {
    await expect(page.getByRole("heading", { level: 2, name: heading, exact: heading !== "Settings" })).toBeVisible();
  }

  const workflow = page.getByRole("region", { name: "Analyse games" });
  await workflow.getByLabel("Lichess username").fill("ExampleUser");
  await workflow.getByLabel("PGN path").fill(`input/${"long-windows-path-segment-".repeat(12)}games.pgn`);
  const settings = page.getByRole("region", { name: "Settings" });
  await expect(settings.getByLabel("Stockfish path")).toBeHidden();
  await page.getByRole("link", { name: "Settings / Advanced" }).click();
  await expect(settings.getByLabel("Stockfish path")).toBeVisible();
  await settings.getByLabel("Stockfish path").fill(`C:\\Users\\ExampleUser\\${"very-long-stockfish-directory\\".repeat(12)}stockfish.exe`);

  for (const viewport of [{ width: 1280, height: 720 }, { width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }

  await page.locator("body").press("Tab");
  await expect.poll(() => page.evaluate(() => document.activeElement?.tagName)).toMatch(/A|BUTTON|INPUT/);
  expect(await page.locator("[id]").evaluateAll((elements) => elements.map((element) => element.id))).toEqual(
    expect.arrayContaining(["analyse", "results", "diagnostics", "settings"]),
  );
  const duplicateIds = await page.locator("[id]").evaluateAll((elements) => {
    const ids = elements.map((element) => element.id);
    return ids.filter((id, index) => ids.indexOf(id) !== index);
  });
  expect(duplicateIds).toEqual([]);
});

test("built FastAPI root keeps saved tokens private and exercises the import, analysis, export, and diagnostics workflow", async ({ page }) => {
  let importCalls = 0;
  let analyseCalls = 0;
  let importOnlyPayload: Record<string, unknown> | null = null;
  let exportPayload: Record<string, unknown> | null = null;
  let diagnosticsPayload: Record<string, unknown> | null = null;

  await page.route("**/api/import-lichess", async (route) => {
    importCalls += 1;
    const payload = route.request().postDataJSON() as Record<string, unknown>;
    if (importCalls === 1) {
      importOnlyPayload = payload;
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ ok: true, out_path: "input/lichess_recent_exampleuser.pgn", stdout: "", stderr: "" }),
    });
  });
  await page.route("**/api/analyse", async (route) => {
    analyseCalls += 1;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        markdown_path: "reports/2026-07-09_exampleuser_recent.md",
        json_path: "reports/2026-07-09_exampleuser_recent.json",
        games_analysed: 3,
        stdout: "",
        stderr: "",
      }),
    });
  });
  await page.route("**/api/export-annotated-pgn", async (route) => {
    exportPayload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ ok: true, out_path: "reports/annotated/exampleuser_annotated.pgn", games_exported: 3, stdout: "", stderr: "" }),
    });
  });
  await page.route("**/api/diagnostics", async (route) => {
    diagnosticsPayload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ ok: true, path: ".coach/diagnostics/bundle-1" }) });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 2, name: "Local readiness" })).toBeVisible();
  await expect(page.getByLabel("Replace saved Lichess token")).toHaveValue("");
  await expect(page.locator("body")).not.toContainText("fake-browser-token");

  const workflow = page.getByRole("region", { name: "Analyse games" });
  await expect(workflow.getByLabel("Rated games only")).toBeChecked();
  await expect(workflow.getByLabel("Performance filter")).toHaveValue("");
  await expect(workflow.getByLabel("Performance filter").locator("option")).toHaveText(["All", "Rapid", "Blitz", "Bullet", "Classical"]);
  await workflow.getByLabel("Lichess username").fill("ExampleUser");
  await workflow.getByText("Advanced import and path options").click();
  await workflow.getByLabel("Performance filter").selectOption("rapid");
  await workflow.getByRole("button", { name: "Import games" }).click();

  await expect(workflow.getByRole("status")).toHaveText("Imported games to input/lichess_recent_exampleuser.pgn. Analyse them from the existing PGN source when ready.");
  expect(importCalls).toBe(1);
  expect(analyseCalls).toBe(0);
  expect(importOnlyPayload).toMatchObject({ username: "ExampleUser", perf: "rapid", rated_only: true });

  await workflow.getByRole("button", { name: "Import and analyse games" }).click();
  await expect(workflow.getByRole("status")).toHaveText("Analysed 3 games. Review the Results section for local outputs.");
  expect(importCalls).toBe(2);
  expect(analyseCalls).toBe(1);

  const results = page.getByRole("region", { name: "Results" });
  await expect(results).toContainText("3 games analysed");
  await expect(results).toContainText("Structured JSON: reports/2026-07-09_exampleuser_recent.json");
  await results.getByRole("button", { name: "Export annotated PGN" }).click();
  await expect(results.getByRole("status")).toHaveText("Exported 3 games to reports/annotated/exampleuser_annotated.pgn.");
  expect(exportPayload).toMatchObject({
    json_path: "reports/2026-07-09_exampleuser_recent.json",
    out_path: "reports/annotated/exampleuser_annotated.pgn",
  });

  const diagnostics = page.getByRole("region", { name: "Diagnostics" });
  await diagnostics.getByText("Show diagnostics options").click();
  await expect(diagnostics.getByLabel("Include PGN in diagnostic bundle")).not.toBeChecked();
  await expect(diagnostics.getByLabel("Include report in diagnostic bundle")).not.toBeChecked();
  await diagnostics.getByRole("button", { name: "Create diagnostic bundle" }).click();
  await expect(diagnostics).toContainText("Diagnostic bundle: .coach/diagnostics/bundle-1");
  expect(diagnosticsPayload).toMatchObject({ include_pgn: false, include_report: false, selected_paths: {} });
});

test("legacy rollback remains available while next compatibility routes redirect to the canonical root", async ({ request }) => {
  const legacy = await request.get("/legacy/");
  const next = await request.get("/next/", { maxRedirects: 0 });
  const nextAsset = await request.get("/next/assets/not-a-route.js", { maxRedirects: 0 });

  expect(legacy.status()).toBe(200);
  expect(legacy.headers()["content-security-policy"]).toBe("default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'");
  expect(await legacy.text()).toContain('src="/static/app.js"');
  expect(next.status()).toBe(307);
  expect(next.headers()["location"]).toBe("/");
  expect(nextAsset.status()).toBe(404);
});
