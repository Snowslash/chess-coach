import { deriveWorkflowPaths, type WorkflowPaths } from "@/lib/paths";

export type WorkflowPathField = keyof WorkflowPaths;
export type WorkflowSourceMode = "import-lichess" | "existing-pgn";

export interface WorkflowState {
  username: string;
  date: string;
  sourceMode: WorkflowSourceMode;
  paths: WorkflowPaths;
  manualPaths: Record<WorkflowPathField, boolean>;
  pathValidity: "valid" | "invalid-username";
}

export type WorkflowAction =
  | { type: "set-username"; username: string; date: string }
  | { type: "set-source-mode"; sourceMode: WorkflowSourceMode }
  | { type: "set-path"; field: WorkflowPathField; value: string }
  | { type: "reset-suggested-paths"; date: string };

const automaticPaths = (): Record<WorkflowPathField, boolean> => ({
  importPgn: false,
  markdown: false,
  json: false,
  annotatedPgn: false,
});

function pathsFor(username: string, date: string): Pick<WorkflowState, "paths" | "pathValidity"> {
  const derived = deriveWorkflowPaths(username, date);
  return {
    paths: derived.paths,
    pathValidity: derived.valid ? "valid" : "invalid-username",
  };
}

function replaceAutomaticPaths(state: WorkflowState, username: string, date: string): WorkflowState {
  const suggested = pathsFor(username, date);
  const paths = { ...state.paths };
  for (const field of Object.keys(paths) as WorkflowPathField[]) {
    if (!state.manualPaths[field]) {
      paths[field] = suggested.paths[field];
    }
  }
  return { ...state, username, date, paths, pathValidity: suggested.pathValidity };
}

function jsonPathFor(markdownPath: string): string {
  return markdownPath.endsWith(".md") ? `${markdownPath.slice(0, -3)}.json` : markdownPath;
}

export function createWorkflowState(username: string, date: string): WorkflowState {
  return {
    username,
    date,
    sourceMode: "import-lichess",
    ...pathsFor(username, date),
    manualPaths: automaticPaths(),
  };
}

export function workflowReducer(state: WorkflowState, action: WorkflowAction): WorkflowState {
  switch (action.type) {
    case "set-username":
      return replaceAutomaticPaths(state, action.username, action.date);
    case "set-source-mode":
      return { ...state, sourceMode: action.sourceMode };
    case "set-path":
      if (action.field === "markdown" && !state.manualPaths.json) {
        return {
          ...state,
          paths: { ...state.paths, markdown: action.value, json: jsonPathFor(action.value) },
          manualPaths: { ...state.manualPaths, markdown: true },
        };
      }
      return {
        ...state,
        paths: { ...state.paths, [action.field]: action.value },
        manualPaths: { ...state.manualPaths, [action.field]: true },
      };
    case "reset-suggested-paths":
      return {
        ...state,
        date: action.date,
        ...pathsFor(state.username, action.date),
        manualPaths: automaticPaths(),
      };
  }
}
