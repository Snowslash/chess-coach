import { createWorkflowState, workflowReducer } from "./workflow-state";

describe("workflow path state", () => {
  it("starts with no real workflow paths until a valid username is supplied", () => {
    const state = createWorkflowState("", "2026-07-09");

    expect(state.paths).toEqual({ importPgn: "", markdown: "", json: "", annotatedPgn: "" });
    expect(state.pathValidity).toBe("invalid-username");
  });

  it("preserves manual paths while username, date, and source mode change", () => {
    let state = createWorkflowState("ExampleUser", "2026-07-09");
    state = workflowReducer(state, { type: "set-path", field: "markdown", value: "reports/my-note.md" });
    expect(state.paths.json).toBe("reports/my-note.json");
    state = workflowReducer(state, { type: "set-username", username: "OtherUser", date: "2026-07-10" });
    state = workflowReducer(state, { type: "set-source-mode", sourceMode: "existing-pgn" });

    expect(state.paths.markdown).toBe("reports/my-note.md");
    expect(state.paths.importPgn).toBe("input/lichess_recent_otheruser.pgn");
    expect(state.paths.json).toBe("reports/2026-07-10_otheruser_recent.json");
    expect(state.sourceMode).toBe("existing-pgn");
  });

  it("resets all manual paths to the current safe recommendations", () => {
    let state = createWorkflowState("ExampleUser", "2026-07-09");
    state = workflowReducer(state, { type: "set-path", field: "importPgn", value: "input/custom.pgn" });
    state = workflowReducer(state, { type: "set-path", field: "markdown", value: "reports/custom.md" });
    state = workflowReducer(state, { type: "reset-suggested-paths", date: "2026-07-10" });

    expect(state.paths).toEqual({
      importPgn: "input/lichess_recent_exampleuser.pgn",
      markdown: "reports/2026-07-10_exampleuser_recent.md",
      json: "reports/2026-07-10_exampleuser_recent.json",
      annotatedPgn: "reports/annotated/exampleuser_annotated.pgn",
    });
    expect(state.manualPaths).toEqual({ importPgn: false, markdown: false, json: false, annotatedPgn: false });
  });
});
