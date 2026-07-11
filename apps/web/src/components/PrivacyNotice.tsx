interface PrivacyNoticeProps {
  storage?: string;
}

export function PrivacyNotice({ storage = "Your reports and diagnostics stay on this computer." }: PrivacyNoticeProps) {
  return (
    <section className="privacy-notice" aria-label="Local privacy">
      <p>
        <strong>Local-only.</strong> Chess Coach runs on your machine; it has no hosted service, analytics, or telemetry.
      </p>
      <p>{storage}</p>
    </section>
  );
}
