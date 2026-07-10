import { useEffect, useState } from "react";

import { PrivacyNotice } from "../../components/PrivacyNotice";
import { ReadinessCard } from "../../components/ReadinessCard";
import { ApiError, getBootstrap, getReadiness } from "../../lib/api";
import type { BootstrapResponse, ReadinessResponse } from "../../lib/api-types";

interface LoadedState {
  bootstrap: BootstrapResponse;
  readiness: ReadinessResponse;
}

export function ReadinessDashboard() {
  const [attempt, setAttempt] = useState(0);
  const [loaded, setLoaded] = useState<LoadedState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoaded(null);
    setError(null);

    Promise.all([getBootstrap({ signal: controller.signal }), getReadiness({ signal: controller.signal })])
      .then(([bootstrap, readiness]) => setLoaded({ bootstrap, readiness }))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof ApiError ? reason.message : "Unable to check local readiness.");
        }
      });

    return () => controller.abort();
  }, [attempt]);

  if (error) {
    return (
      <section aria-labelledby="readiness-heading" className="readiness-section">
        <h2 id="readiness-heading">Local readiness</h2>
        <p role="alert">{error}</p>
        <button type="button" onClick={() => setAttempt((current) => current + 1)}>
          Retry readiness check
        </button>
      </section>
    );
  }

  if (!loaded) {
    return (
      <section aria-labelledby="readiness-heading" className="readiness-section" aria-busy="true">
        <h2 id="readiness-heading">Local readiness</h2>
        <p>Checking local readiness…</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="readiness-heading" className="readiness-section">
      <h2 id="readiness-heading">Local readiness</h2>
      <PrivacyNotice storage={loaded.bootstrap.privacy.storage} />
      <div className="readiness-grid">
        <ReadinessCard label="Stockfish" item={loaded.readiness.stockfish} />
        <ReadinessCard label="Maia" item={loaded.readiness.maia} />
      </div>
    </section>
  );
}
