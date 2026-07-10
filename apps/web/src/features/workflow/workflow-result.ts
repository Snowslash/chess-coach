export interface WorkflowResult {
  importedPgnPath: string | null;
  markdownPath: string;
  jsonPath: string;
  annotatedPgnPath: string;
  gamesAnalysed: number;
  stdout: string;
  stderr: string;
}

export function curatedWorkflowMessages(result: WorkflowResult): string[] {
  return [
    `Analysed ${result.gamesAnalysed} ${result.gamesAnalysed === 1 ? "game" : "games"}.`,
    `Report ready: ${result.markdownPath}`,
  ];
}
