export interface WorkflowPaths {
  importPgn: string;
  markdown: string;
  json: string;
  annotatedPgn: string;
}

export type WorkflowPathDerivation =
  | { valid: true; paths: WorkflowPaths }
  | { valid: false; paths: WorkflowPaths };

const EMPTY_PATHS: WorkflowPaths = {
  importPgn: "",
  markdown: "",
  json: "",
  annotatedPgn: "",
};

const SAFE_LICHESS_USERNAME = /^[A-Za-z0-9][A-Za-z0-9_-]{0,28}$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function deriveWorkflowPaths(username: string, date: string): WorkflowPathDerivation {
  const safeUsername = username.trim();
  if (!SAFE_LICHESS_USERNAME.test(safeUsername) || !ISO_DATE.test(date)) {
    return { valid: false, paths: { ...EMPTY_PATHS } };
  }

  const pathUsername = safeUsername.toLowerCase();
  const reportStem = `reports/${date}_${pathUsername}_recent`;
  return {
    valid: true,
    paths: {
      importPgn: `input/lichess_recent_${pathUsername}.pgn`,
      markdown: `${reportStem}.md`,
      json: `${reportStem}.json`,
      annotatedPgn: `reports/annotated/${pathUsername}_annotated.pgn`,
    },
  };
}
