import { useQuery } from "@tanstack/react-query";

import { getStats } from "../../api/client";
import { Badge, ErrorState, LoadingState } from "../../components/Status";
import { formatNumber } from "../../lib/format";

export function OverviewPage() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: getStats });

  if (stats.isLoading) return <LoadingState />;
  if (stats.error) return <ErrorState error={stats.error} />;

  const payload = stats.data;

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Local control plane</p>
          <h1>Overview</h1>
        </div>
        <Badge tone="good">online</Badge>
      </header>

      <div className="metric-grid">
        <Metric label="Memory units" value={payload?.unit_count} />
        <Metric label="Dialogues" value={payload?.dialogue_count} />
        <Metric label="Operation logs" value={payload?.operation_log_count} />
        <Metric label="Index documents" value={payload?.index_document_count} />
      </div>

      <section className="panel">
        <h2>Storage</h2>
        <dl className="definition-grid">
          <dt>Backend</dt>
          <dd>{String(payload?.store ?? "unknown")}</dd>
          <dt>Path</dt>
          <dd>{String(payload?.path ?? "unknown")}</dd>
          <dt>Schema</dt>
          <dd>{String(payload?.schema_version ?? "unknown")}</dd>
        </dl>
      </section>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{formatNumber(value)}</strong>
    </div>
  );
}
