import { getNativeBridge, isProjectRelativePath } from "./native-bridge";

describe("native desktop bridge", () => {
  afterEach(() => {
    delete (window as Window & { chessCoachDesktop?: unknown }).chessCoachDesktop;
  });

  it("returns null in browser mode and only accepts project-relative paths", () => {
    expect(getNativeBridge()).toBeNull();
    expect(isProjectRelativePath("reports/latest.md")).toBe(true);
    expect(isProjectRelativePath("../outside.md")).toBe(false);
    expect(isProjectRelativePath("C:\\outside.md")).toBe(false);
    expect(isProjectRelativePath("/tmp/outside.md")).toBe(false);
  });

  it("recognises only the narrow native bridge contract", () => {
    const openPath = vi.fn();
    Object.assign(window, { chessCoachDesktop: { openPath } });

    expect(getNativeBridge()).toEqual({ openPath });
  });
});
