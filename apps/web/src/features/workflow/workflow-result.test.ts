import { curatedWorkflowMessages, type WorkflowResult } from "./workflow-result";

const result: WorkflowResult = {
  importedPgnPath: "input/lichess_recent_exampleuser.pgn",
  markdownPath: "reports/2026-07-09_exampleuser_recent.md",
  jsonPath: "reports/2026-07-09_exampleuser_recent.json",
  annotatedPgnPath: "reports/annotated/exampleuser_annotated.pgn",
  gamesAnalysed: 3,
  stdout: "runner stdout token=workflow-marker",
  stderr: "runner stderr authorization: Bearer workflow-marker",
};

describe("curatedWorkflowMessages", () => {
  it("uses only curated analysis metadata and never runner output", () => {
    expect(curatedWorkflowMessages(result)).toEqual([
      "Analysed 3 games.",
      "Report ready: reports/2026-07-09_exampleuser_recent.md",
    ]);
  });
});
