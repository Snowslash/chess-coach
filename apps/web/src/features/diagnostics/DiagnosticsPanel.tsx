import { useEffect, useMemo, useState } from "react";

import { createDiagnostics, getBootstrap, getReadiness } from "@/lib/api";
import type { BootstrapResponse, ReadinessResponse } from "@/lib/api-types";

import type { WorkflowResult } from "../workflow/workflow-result";

export interface DiagnosticsPanelProps {
  result: WorkflowResult | null;
  recentMessages: string[];
}

function redactClientMessage(message: string): string {
  return message
    .replace(/\bauthorization\s*:\s*(?:\*+\s*)?(?:bearer\s+)?[^\s,;]+/gi, "authorization: [redacted]")
    .replace(/\btoken\s*[=:]\s*[^\s,;]+/gi, "token=[redacted]")
    .replace(/\b(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]+/gi, "[redacted]")
    .replace(/\b[a-f0-9]{40}\b/gi, "[redacted]");
}

function displayBundlePath(path: string): string | null {
  const coachDirectory = path.indexOf(".coach/");
  return coachDirectory >= 0 ? path.slice(coachDirectory) : null;
}

export function DiagnosticsPanel({ result, recentMessages }: DiagnosticsPanelProps) {
  const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [includePgn, setIncludePgn] = useState(false);
  const [includeReport, setIncludeReport] = useState(false);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState("");
  const [bundlePath, setBundlePath] = useState("");

  const safeMessages = useMemo(() => recentMessages.map(redactClientMessage).filter(Boolean).slice(-10), [recentMessages]);

  useEffect(() => {
    let active = true;
    void Promise.all([getBootstrap(), getReadiness()])
      .then(([nextBootstrap, nextReadiness]) => {
        if (active) {
          setBootstrap(nextBootstrap);
          setReadiness(nextReadiness);
        }
      })
      .catch(() => {
        if (active) {
          setMessage("Local environment summary could not load.");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const createBundle = async () => {
    const selectedPaths: Record<string, string> = {};
    const includePgnPath = Boolean(includePgn && result?.importedPgnPath);
    const includeReportPath = Boolean(includeReport && result?.markdownPath);
    if (includePgnPath && result?.importedPgnPath) {
      selectedPaths.pgn = result.importedPgnPath;
    }
    if (includeReportPath && result) {
      selectedPaths.report = result.markdownPath;
    }
    setCreating(true);
    setMessage("");
    setBundlePath("");
    try {
      const created = await createDiagnostics({
        include_pgn: includePgnPath,
        include_report: includeReportPath,
        selected_paths: selectedPaths,
        recent_logs: safeMessages,
      });
      const safeBundlePath = displayBundlePath(created.path);
      if (safeBundlePath) {
        setBundlePath(safeBundlePath);
      } else {
        setMessage("Diagnostic bundle created locally.");
      }
    } catch (_error) {
      setMessage("Diagnostic bundle could not be created.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <section aria-labelledby="diagnostics-heading" className="diagnostics-section" id="diagnostics">
      <div className="diagnostics-intro">
        <h2 id="diagnostics-heading">Diagnostics</h2>
      </div>
      <details>
        <summary>Show diagnostics options</summary>
        <p className="field-help">Create a local support bundle only when needed. Nothing is uploaded.</p>
        <div className="diagnostics-summary">
          <p>Local-only: {bootstrap?.privacy.local_only ? "yes" : bootstrap ? "no" : "checking"}</p>
          <p>Telemetry: {bootstrap?.privacy.telemetry === false ? "disabled" : bootstrap ? "unknown" : "checking"}</p>
          <p>Stockfish: {readiness ? `${readiness.stockfish.status} — ${readiness.stockfish.details}` : "checking"}</p>
          <p>Maia: {readiness ? `${readiness.maia.status} — ${readiness.maia.details}` : "checking"}</p>
        </div>
        <fieldset className="diagnostics-options" disabled={creating}>
          <legend>Optional local inclusion</legend>
          <label className="field-group field-group--checkbox" htmlFor="diagnostics-include-pgn">
            <input checked={includePgn} className="field-checkbox" disabled={!result?.importedPgnPath || creating} id="diagnostics-include-pgn" onChange={(event) => setIncludePgn(event.target.checked)} type="checkbox" />
            <span className="field-label">Include PGN in diagnostic bundle</span>
          </label>
          <label className="field-group field-group--checkbox" htmlFor="diagnostics-include-report">
            <input checked={includeReport} className="field-checkbox" disabled={!result || creating} id="diagnostics-include-report" onChange={(event) => setIncludeReport(event.target.checked)} type="checkbox" />
            <span className="field-label">Include report in diagnostic bundle</span>
          </label>
        </fieldset>
        {safeMessages.length > 0 ? (
          <details className="diagnostics-activity">
            <summary>Visible activity included in the bundle</summary>
            <ul>{safeMessages.map((entry, index) => <li key={`${index}-${entry}`}>{entry}</li>)}</ul>
          </details>
        ) : null}
        <div className="workflow-actions">
          <button disabled={creating} onClick={() => void createBundle()} type="button">{creating ? "Creating diagnostic bundle…" : "Create diagnostic bundle"}</button>
        </div>
        {bundlePath ? <p className="diagnostics-bundle">Diagnostic bundle: {bundlePath}</p> : null}
        <p aria-live="polite" className="workflow-status" role="status">{message}</p>
      </details>
    </section>
  );
}
