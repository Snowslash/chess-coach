import { deriveWorkflowPaths } from "./paths";

describe("deriveWorkflowPaths", () => {
  it("derives safe username- and date-specific import and output paths", () => {
    expect(deriveWorkflowPaths("Example-User", "2026-07-09")).toEqual({
      valid: true,
      paths: {
        importPgn: "input/lichess_recent_example-user.pgn",
        markdown: "reports/2026-07-09_example-user_recent.md",
        json: "reports/2026-07-09_example-user_recent.json",
        annotatedPgn: "reports/annotated/example-user_annotated.pgn",
      },
    });
  });

  it("leaves every workflow path blank when the username is blank or invalid", () => {
    for (const username of ["", "unsafe name", "../escape", "name@example"]) {
      expect(deriveWorkflowPaths(username, "2026-07-09")).toEqual({
        valid: false,
        paths: {
          importPgn: "",
          markdown: "",
          json: "",
          annotatedPgn: "",
        },
      });
    }
  });

  it("never derives the sample fixture as an import source", () => {
    const derived = deriveWorkflowPaths("ExampleUser", "2026-07-09");

    expect(derived.paths.importPgn).not.toBe("input/sample_games.pgn");
  });
});
