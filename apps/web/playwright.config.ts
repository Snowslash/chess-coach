import { fileURLToPath } from "node:url";

import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:8899",
    browserName: "chromium",
    headless: true,
  },
  webServer: {
    command: "python3 -m chess_coach web --host 127.0.0.1 --port 8899",
    cwd: fileURLToPath(new URL("../..", import.meta.url)),
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
