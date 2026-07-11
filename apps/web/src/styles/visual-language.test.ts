/// <reference types="node" />

import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(path.join(process.cwd(), "src/styles/globals.css"), "utf8");
const shell = readFileSync(path.join(process.cwd(), "src/app/AppShell.tsx"), "utf8");

const sharedTokens = [
  "--background: #f4f0e8",
  "--foreground: #1d1b18",
  "--card: #fbf8f2",
  "--primary: #8a1538",
  "--muted-foreground: #655e55",
  "--border: #c7b8a5",
  "--background: #1d1b18",
  "--foreground: #f4f0e8",
  "--card: #24211d",
  "--primary: #a3264d",
  "--ring: #c43b63",
];

describe("shared visual language contract", () => {
  it("keeps the canonical light and dark palette", () => {
    for (const token of sharedTokens) expect(css).toContain(token);
  });

  it("keeps restrained burgundy headings, square controls and no eyebrow copy", () => {
    expect(css).toMatch(/h1,\s*h2,\s*h3\s*\{\s*color:\s*var\(--primary\)/s);
    expect(css).toContain("border-radius: 0.125rem");
    expect(css).toContain("font-size: clamp(1.875rem, 5vw, 2.25rem)");
    expect(css).not.toContain(".eyebrow");
    expect(shell).not.toContain("eyebrow");
  });
});
