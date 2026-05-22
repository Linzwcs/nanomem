import { useQuery } from "@tanstack/react-query";

import { getStats } from "../../api/client";
import { Badge, ErrorState, LoadingState } from "../../components/Status";
import { jsonPreview } from "../../lib/format";

export function IndexHealthPage() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: getStats });

  if (stats.isLoading) return <LoadingState />;
  if (stats.error) return <ErrorState error={stats.error} />;

  const index = stats.data?.metadata.index ?? {};
  const backend = String(stats.data?.index_backend ?? "unknown");

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Retrieval backend</p>
          <h1>Index Health</h1>
        </div>
        <Badge tone="neutral">{backend}</Badge>
      </header>

      <section className="panel">
        <dl className="definition-grid">
          <div className="definition-row">
            <dt>backend</dt>
            <dd>{backend}</dd>
          </div>
          <div className="definition-row">
            <dt>document_count</dt>
            <dd>{String(stats.data?.index_document_count ?? "unknown")}</dd>
          </div>
          {Object.entries(index).map(([key, value]) => (
            <div className="definition-row" key={key}>
              <dt>{key}</dt>
              <dd>{typeof value === "object" ? jsonPreview(value) : String(value)}</dd>
            </div>
          ))}
        </dl>
      </section>
    </section>
  );
}
