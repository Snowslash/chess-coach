export interface WorkflowCapabilities {
  pathInput: "project-relative-text";
  canChoosePath: boolean;
  canOpenOutput: boolean;
}

export const browserWorkflowCapabilities: WorkflowCapabilities = {
  pathInput: "project-relative-text",
  canChoosePath: false,
  canOpenOutput: false,
};
