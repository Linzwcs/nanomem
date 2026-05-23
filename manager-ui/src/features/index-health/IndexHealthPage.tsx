import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getStats, rebuildIndex } from "../../api/client";
import { Badge, ErrorState, LoadingState } from "../../components/Status";
import { formatTime, jsonPreview } from "../../lib/format";

export function IndexHealthPage() {
  const queryClient = useQueryClient();
  const stats = useQuery({ queryKey: ["stats"], queryFn: getStats });
  const rebuild = useMutation({
    mutationFn: () => rebuildIndex(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      queryClient.invalidateQueries({ queryKey: ["operation-logs"] });
    },
  });

  if (stats.isLoading) return <LoadingState />;
  if (stats.error) return <ErrorState error={stats.error} />;

  const payload = stats.data;
  const index = stats.data?.metadata.index ?? {};
  const backend = String(stats.data?.index_backend ?? "unknown");
  const health = payload?.index_health ?? "unknown";
  const healthTone = health === "synced" ? "good" : health === "stale" ? "warn" : "muted";

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Retrieval backend</p>
          <h1>Index Health</h1>
        </div>
        <Badge tone={healthTone}>{health}</Badge>
      </header>

      <div className="metric-grid">
        <Metric label="Active units" value={payload?.active_unit_count} />
        <Metric label="Index documents" value={payload?.index_document_count} />
        <Metric label="Delta" value={payload?.index_unit_delta} />
        <Metric label="Backend" value={backend} />
      </div>

      <section className="panel">
        <div className="panel-toolbar">
          <div>
            <h2>State</h2>
            <p className="muted-line">
              Last reindex: {formatTime(payload?.last_reindex_at)}
            </p>
          </div>
          <button
            type="button"
            disabled={rebuild.isPending}
            onClick={() => rebuild.mutate()}
          >
            {rebuild.isPending ? "Rebuilding..." : "Rebuild index"}
          </button>
        </div>
        {rebuild.error && <ErrorState error={rebuild.error} />}
        {rebuild.data && (
          <div className="notice">
            Reindexed {rebuild.data.indexed_unit_count} units into{" "}
            {rebuild.data.index_backend}.
          </div>
        )}
        <dl className="definition-grid">
          <div className="definition-row">
            <dt>backend</dt>
            <dd>{backend}</dd>
          </div>
          <div className="definition-row">
            <dt>health</dt>
            <dd>{health}</dd>
          </div>
          <div className="definition-row">
            <dt>active_unit_count</dt>
            <dd>{String(payload?.active_unit_count ?? "unknown")}</dd>
          </div>
          <div className="definition-row">
            <dt>document_count</dt>
            <dd>{String(stats.data?.index_document_count ?? "unknown")}</dd>
          </div>
          <div className="definition-row">
            <dt>unit_delta</dt>
            <dd>{String(payload?.index_unit_delta ?? "unknown")}</dd>
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

function Metric({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{String(value ?? "unknown")}</strong>
    </div>
  );
}
