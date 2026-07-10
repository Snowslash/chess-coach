import { useEffect, useState } from "react";

import { ApiError, exportAnnotatedPgn } from "@/lib/api";
import { getNativeBridge, isProjectRelativePath } from "@/lib/native-bridge";

import type { WorkflowResult } from "../workflow/workflow-result";

export interface ResultsPageProps {
  result: WorkflowResult | null;
}

function resultError(errors: Record<string, string>, field: string) {
  const message = errors[field];
  return message ? <p className="field-error" id={`${field}-error`}>{message}</p> : null;
}

export function ResultsPage({ result }: ResultsPageProps) {
  const nativeBridge = getNativeBridge();
  const [jsonPath, setJsonPath] = useState("");
  const [outPath, setOutPath] = useState("");
  const [maxGames, setMaxGames] = useState(10);
  const [criticalOnly, setCriticalOnly] = useState(true);
  const [includeAllMoves, setIncludeAllMoves] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  useEffect(() => {
    setJsonPath(result?.jsonPath ?? "");
    setOutPath(result?.annotatedPgnPath ?? "");
    setErrors({});
    setMessage("");
  }, [result]);

  const exportPgn = async () => {
    if (!result) {
      return;
    }
    setExporting(true);
    setErrors({});
    setMessage("");
    try {
      const exported = await exportAnnotatedPgn({
        json_path: jsonPath,
        out_path: outPath,
        max_games: maxGames,
        critical_only: criticalOnly,
        include_all_moves: includeAllMoves,
      });
      setMessage(`Exported ${exported.games_exported} ${exported.games_exported === 1 ? "game" : "games"} to ${exported.out_path}.`);
    } catch (error) {
      setErrors(error instanceof ApiError ? error.errors : {});
      setMessage("Annotated PGN export could not complete.");
    } finally {
      setExporting(false);
    }
  };

  const openNativePath = (projectRelativePath: string) => {
    if (nativeBridge && isProjectRelativePath(projectRelativePath)) {
      void nativeBridge.openPath(projectRelativePath);
    }
  };

  return (
    <section aria-labelledby="results-heading" className="results-section" id="results">
      <div className="results-intro">
        <div>
          <h2 id="results-heading">Results</h2>
        </div>
        <p>Open generated files from the local project folder in browser mode.</p>
      </div>
      {!result ? <p className="results-empty">No analysis result yet. Analyse games to prepare local outputs.</p> : (
        <>
          <div className="results-summary">
            <p>{result.gamesAnalysed} {result.gamesAnalysed === 1 ? "game" : "games"} analysed</p>
            <p>{result.importedPgnPath ? `Imported PGN: ${result.importedPgnPath}` : "Existing PGN analysed."}</p>
            <p>Markdown report: {result.markdownPath}</p>
            <p>Structured JSON: {result.jsonPath}</p>
          </div>
          {nativeBridge ? (
            <div aria-label="Open local results" className="workflow-actions">
              <button onClick={() => openNativePath(result.markdownPath)} type="button">Open report</button>
              <button onClick={() => openNativePath(result.jsonPath)} type="button">Open JSON</button>
              <button onClick={() => openNativePath(result.annotatedPgnPath)} type="button">Open annotated PGN</button>
            </div>
          ) : null}

          <form className="results-export" onSubmit={(event) => { event.preventDefault(); void exportPgn(); }}>
            <h3>Export annotated PGN</h3>
            <div className="workflow-grid">
              <label className="field-group workflow-field--wide" htmlFor="results-json-path">
                <span className="field-label">Analysis JSON source path</span>
                <input aria-describedby={errors.json_path ? "json_path-error" : undefined} aria-invalid={Boolean(errors.json_path)} className="field-input" disabled={exporting} id="results-json-path" onChange={(event) => setJsonPath(event.target.value)} value={jsonPath} />
                {resultError(errors, "json_path")}
              </label>
              <label className="field-group workflow-field--wide" htmlFor="results-annotated-path">
                <span className="field-label">Annotated PGN output path</span>
                <input aria-describedby={errors.out_path ? "out_path-error" : undefined} aria-invalid={Boolean(errors.out_path)} className="field-input" disabled={exporting} id="results-annotated-path" onChange={(event) => setOutPath(event.target.value)} value={outPath} />
                {resultError(errors, "out_path")}
              </label>
              <label className="field-group" htmlFor="results-max-games">
                <span className="field-label">Maximum games</span>
                <input className="field-input" disabled={exporting} id="results-max-games" min="1" onChange={(event) => setMaxGames(Number(event.target.value))} type="number" value={maxGames} />
              </label>
              <label className="field-group field-group--checkbox" htmlFor="results-critical-only">
                <input checked={criticalOnly} className="field-checkbox" disabled={exporting} id="results-critical-only" onChange={(event) => setCriticalOnly(event.target.checked)} type="checkbox" />
                <span className="field-label">Critical moments only</span>
              </label>
              <label className="field-group field-group--checkbox" htmlFor="results-all-moves">
                <input checked={includeAllMoves} className="field-checkbox" disabled={exporting} id="results-all-moves" onChange={(event) => setIncludeAllMoves(event.target.checked)} type="checkbox" />
                <span className="field-label">Include all analysed moves</span>
              </label>
            </div>
            <div className="workflow-actions">
              <button disabled={exporting} type="submit">{exporting ? "Exporting annotated PGN…" : "Export annotated PGN"}</button>
            </div>
          </form>
        </>
      )}
      <p aria-live="polite" className="workflow-status" role="status">{message}</p>
    </section>
  );
}
