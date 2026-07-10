import type { ReadinessItem } from "../lib/api-types";

interface ReadinessCardProps {
  label: string;
  item: ReadinessItem;
}

function statusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

export function ReadinessCard({ label, item }: ReadinessCardProps) {
  return (
    <article className="readiness-card" aria-label={`${label}: ${statusLabel(item.status)}`}>
      <div className="readiness-card__heading">
        <h3>{label}</h3>
        <span className={`status-badge status-badge--${item.status}`}>{statusLabel(item.status)}</span>
      </div>
      <p>{item.details}</p>
    </article>
  );
}
