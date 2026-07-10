import { useState } from "react";

import { AppShell } from "./app/AppShell";
import { ReadinessDashboard } from "./features/bootstrap/ReadinessDashboard";
import { DiagnosticsPanel } from "./features/diagnostics/DiagnosticsPanel";
import { ResultsPage } from "./features/results/ResultsPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { curatedWorkflowMessages, type WorkflowResult } from "./features/workflow/workflow-result";
import { WorkflowSection } from "./features/workflow/WorkflowSection";

export function App() {
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const visibleMessages = result ? curatedWorkflowMessages(result) : [];

  return (
    <AppShell>
      <ReadinessDashboard />
      <WorkflowSection onResult={setResult} />
      <ResultsPage result={result} />
      <DiagnosticsPanel recentMessages={visibleMessages} result={result} />
      <SettingsPage />
    </AppShell>
  );
}
