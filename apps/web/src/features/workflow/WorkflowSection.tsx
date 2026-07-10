import { useReducer, useState } from "react";

import { analysePgn, ApiError, importLichess, testLichess } from "@/lib/api";
import type { AnalyseResponse } from "@/lib/api-types";

import type { WorkflowResult } from "./workflow-result";
import { createWorkflowState, workflowReducer, type WorkflowPathField, type WorkflowSourceMode } from "./workflow-state";

type WorkflowPhase = "idle" | "checking" | "importing" | "analyzing" | "success" | "error";

export interface WorkflowSectionProps {
  today?: () => string;
  onResult?: (result: WorkflowResult) => void;
}

const DEFAULT_MAX_GAMES = 20;

function fieldError(errors: Record<string, string>, field: string) {
  const message = errors[field];
  return message ? <p className="field-error" id={`${field}-error`}>{message}</p> : null;
}

export function WorkflowSection({ onResult, today = () => new Date().toISOString().slice(0, 10) }: WorkflowSectionProps) {
  const currentDate = today();
  const [workflow, dispatch] = useReducer(workflowReducer, createWorkflowState("", currentDate));
  const [phase, setPhase] = useState<WorkflowPhase>("idle");
  const [message, setMessage] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [maxGames, setMaxGames] = useState(DEFAULT_MAX_GAMES);
  const [perf, setPerf] = useState("");
  const [ratedOnly, setRatedOnly] = useState(true);
  const [sinceDays, setSinceDays] = useState("");

  const busy = phase === "checking" || phase === "importing" || phase === "analyzing";
  const usernameValid = workflow.pathValidity === "valid";

  const updatePath = (field: WorkflowPathField, value: string) => {
    dispatch({ type: "set-path", field, value });
    setErrors((current) => {
      const { [field === "importPgn" ? "pgn_path" : field === "markdown" ? "out_path" : field]: _resolved, ...remaining } = current;
      return remaining;
    });
  };

  const updateUsername = (username: string) => {
    dispatch({ type: "set-username", username, date: currentDate });
    setErrors((current) => {
      const { username: _resolved, ...remaining } = current;
      return remaining;
    });
  };

  const setSourceMode = (sourceMode: WorkflowSourceMode) => {
    dispatch({ type: "set-source-mode", sourceMode });
    setMessage("");
  };

  const captureError = (error: unknown, fallback: string) => {
    setPhase("error");
    setErrors(error instanceof ApiError ? error.errors : {});
    setMessage(fallback);
  };

  const checkLichess = async () => {
    setPhase("checking");
    setErrors({});
    setMessage("");
    try {
      const response = await testLichess({ username: workflow.username, token: "" });
      setPhase("idle");
      setMessage(response.message);
    } catch (error) {
      captureError(error, "Lichess access could not be checked.");
    }
  };

  const recordAnalysis = (analysis: AnalyseResponse, importedPgnPath: string | null) => {
    onResult?.({
      importedPgnPath,
      markdownPath: analysis.markdown_path,
      jsonPath: analysis.json_path,
      annotatedPgnPath: workflow.paths.annotatedPgn,
      gamesAnalysed: analysis.games_analysed,
      stdout: analysis.stdout,
      stderr: analysis.stderr,
    });
    setPhase("success");
    setMessage(`Analysed ${analysis.games_analysed} ${analysis.games_analysed === 1 ? "game" : "games"}. Review the Results section for local outputs.`);
  };

  const importRecentGames = () => importLichess({
    username: workflow.username,
    max_games: maxGames,
    perf: perf || null,
    rated_only: ratedOnly,
    since_days: sinceDays ? Number(sinceDays) : null,
    out_path: workflow.paths.importPgn,
  });

  const importGames = async () => {
    setErrors({});
    setMessage("");
    setPhase("importing");
    try {
      const imported = await importRecentGames();
      setPhase("success");
      setMessage(`Imported games to ${imported.out_path}. Analyse them from the existing PGN source when ready.`);
    } catch (error) {
      captureError(error, "Import could not complete.");
    }
  };

  const runWorkflow = async () => {
    setErrors({});
    setMessage("");
    try {
      if (workflow.sourceMode === "import-lichess") {
        setPhase("importing");
        const imported = await importRecentGames();
        setPhase("analyzing");
        const analysis = await analysePgn({
          username: workflow.username,
          pgn_path: imported.out_path,
          out_path: workflow.paths.markdown,
          mock: false,
        });
        recordAnalysis(analysis, imported.out_path);
        return;
      }

      setPhase("analyzing");
      const analysis = await analysePgn({
        username: workflow.username,
        pgn_path: workflow.paths.importPgn,
        out_path: workflow.paths.markdown,
        mock: false,
      });
      recordAnalysis(analysis, null);
    } catch (error) {
      captureError(error, "Import and analysis could not complete.");
    }
  };

  const primaryLabel = phase === "analyzing"
      ? "Analysing games…"
      : workflow.sourceMode === "import-lichess"
        ? "Import and analyse games"
        : "Analyse existing PGN";
  const importOnlyLabel = phase === "importing" ? "Importing games…" : "Import games";
  const importOnlyActionDisabled = busy || !workflow.paths.importPgn;
  const analysisActionDisabled = busy || !workflow.paths.importPgn || !workflow.paths.markdown;

  return (
    <section aria-labelledby="analyse-heading" className="workflow-section" id="analyse">
      <div className="workflow-intro">
        <div>
          <h2 id="analyse-heading">Analyse games</h2>
        </div>
        <p>Import recent public games or analyse a project-relative PGN already in this project.</p>
      </div>

      <fieldset className="workflow-source" disabled={busy}>
        <legend>Game source</legend>
        <div aria-label="Game source" role="radiogroup">
          <label>
            <input checked={workflow.sourceMode === "import-lichess"} name="source-mode" onChange={() => setSourceMode("import-lichess")} type="radio" value="import-lichess" />
            Import recent public Lichess games
          </label>
          <label>
            <input checked={workflow.sourceMode === "existing-pgn"} name="source-mode" onChange={() => setSourceMode("existing-pgn")} type="radio" value="existing-pgn" />
            Analyse an existing project-relative PGN
          </label>
        </div>
      </fieldset>

      <div className="workflow-grid">
        <label className="field-group" htmlFor="workflow-username">
          <span className="field-label">Lichess username</span>
          <input aria-describedby={errors.username ? "username-error" : undefined} aria-invalid={Boolean(errors.username)} className="field-input" disabled={busy} id="workflow-username" onChange={(event) => updateUsername(event.target.value)} value={workflow.username} />
          {fieldError(errors, "username")}
        </label>
        <label className="field-group" htmlFor="workflow-pgn-path">
          <span className="field-label">PGN path</span>
          <input aria-describedby={errors.pgn_path ? "pgn_path-error" : undefined} aria-invalid={Boolean(errors.pgn_path)} className="field-input" disabled={busy} id="workflow-pgn-path" onChange={(event) => updatePath("importPgn", event.target.value)} value={workflow.paths.importPgn} />
          {fieldError(errors, "pgn_path")}
        </label>
        <label className="field-group workflow-field--wide" htmlFor="workflow-markdown-path">
          <span className="field-label">Markdown report output path</span>
          <input aria-describedby={errors.out_path ? "out_path-error" : undefined} aria-invalid={Boolean(errors.out_path)} className="field-input" disabled={busy} id="workflow-markdown-path" onChange={(event) => updatePath("markdown", event.target.value)} value={workflow.paths.markdown} />
          {fieldError(errors, "out_path")}
        </label>
      </div>
      {!usernameValid ? <p className="field-help">Enter a valid Lichess username to see safe workflow path suggestions.</p> : null}
      <p className="field-help">Browser mode accepts project-relative paths only.</p>

      <div className="workflow-actions">
        <button disabled={busy || !usernameValid} onClick={() => void checkLichess()} type="button">{phase === "checking" ? "Testing Lichess access…" : "Test Lichess access"}</button>
        {workflow.sourceMode === "import-lichess" ? (
          <>
            <button disabled={importOnlyActionDisabled || !usernameValid} onClick={() => void importGames()} type="button">{importOnlyLabel}</button>
            <button disabled={analysisActionDisabled || !usernameValid} onClick={() => void runWorkflow()} type="button">{primaryLabel}</button>
          </>
        ) : <button disabled={analysisActionDisabled || !usernameValid} onClick={() => void runWorkflow()} type="button">{primaryLabel}</button>}
        <button className="button--secondary" disabled={busy} onClick={() => dispatch({ type: "reset-suggested-paths", date: currentDate })} type="button">Reset suggested paths</button>
      </div>

      <details className="advanced-settings">
        <summary>Advanced import and path options</summary>
        <div className="workflow-grid">
          <label className="field-group" htmlFor="workflow-max-games">
            <span className="field-label">Maximum games</span>
            <input className="field-input" disabled={busy || workflow.sourceMode !== "import-lichess"} id="workflow-max-games" max="200" min="1" onChange={(event) => setMaxGames(Number(event.target.value))} type="number" value={maxGames} />
          </label>
          <label className="field-group" htmlFor="workflow-performance">
            <span className="field-label">Performance filter</span>
            <select aria-describedby={errors.perf ? "perf-error" : undefined} aria-invalid={Boolean(errors.perf)} className="field-input" disabled={busy || workflow.sourceMode !== "import-lichess"} id="workflow-performance" onChange={(event) => setPerf(event.target.value)} value={perf}>
              <option value="">All</option>
              <option value="rapid">Rapid</option>
              <option value="blitz">Blitz</option>
              <option value="bullet">Bullet</option>
              <option value="classical">Classical</option>
            </select>
            {fieldError(errors, "perf")}
          </label>
          <label className="field-group" htmlFor="workflow-since-days">
            <span className="field-label">Since days</span>
            <input className="field-input" disabled={busy || workflow.sourceMode !== "import-lichess"} id="workflow-since-days" min="1" onChange={(event) => setSinceDays(event.target.value)} type="number" value={sinceDays} />
          </label>
          <label className="field-group field-group--checkbox" htmlFor="workflow-rated-only">
            <input checked={ratedOnly} className="field-checkbox" disabled={busy || workflow.sourceMode !== "import-lichess"} id="workflow-rated-only" onChange={(event) => setRatedOnly(event.target.checked)} type="checkbox" />
            <span className="field-label">Rated games only</span>
          </label>
          <label className="field-group workflow-field--wide" htmlFor="workflow-json-path">
            <span className="field-label">Structured JSON output path</span>
            <input className="field-input" disabled={busy} id="workflow-json-path" onChange={(event) => updatePath("json", event.target.value)} value={workflow.paths.json} />
          </label>
          <label className="field-group workflow-field--wide" htmlFor="workflow-annotated-path">
            <span className="field-label">Annotated PGN output path</span>
            <input className="field-input" disabled={busy} id="workflow-annotated-path" onChange={(event) => updatePath("annotatedPgn", event.target.value)} value={workflow.paths.annotatedPgn} />
          </label>
        </div>
      </details>

      <p aria-live="polite" className="workflow-status" role="status">{message}</p>
    </section>
  );
}
