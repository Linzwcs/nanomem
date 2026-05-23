import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, RefreshCw } from "lucide-react";

import { getStats, rebuildIndex } from "../../api/client";
import { Badge, ErrorState, LoadingState } from "../../components/Status";
import { formatNumber, formatTime, jsonPreview } from "../../lib/format";

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
      <header className="page-header memory-page-header">
        <div>
          <p className="eyebrow">Retrieval backend</p>
          <h1>Index Health</h1>
        </div>
        <div className="header-actions">
          <Badge tone={healthTone}>{health}</Badge>
          <button
            type="button"
            disabled={rebuild.isPending}
            onClick={() => rebuild.mutate()}
          >
            <span className="button-content">
              {rebuild.isPending ? (
                <Loader2 aria-hidden="true" className="loading-spinner" size={16} />
              ) : (
                <RefreshCw aria-hidden="true" size={16} />
              )}
              {rebuild.isPending ? "Rebuilding" : "Rebuild index"}
            </span>
          </button>
        </div>
      </header>

      <div className="results-strip">
        <div className="filter-chip-list">
          <span className="filter-hint">Backend {backend}</span>
        </div>
        <span className="result-count">
          Last reindex {formatTime(payload?.last_reindex_at)}
        </span>
      </div>

      <div className="metric-grid">
        <Metric label="Active units" value={payload?.active_unit_count} />
        <Metric label="Index documents" value={payload?.index_document_count} />
        <Metric label="Delta" value={payload?.index_unit_delta} />
        <Metric label="Backend" value={backend} />
      </div>

      <section className="panel table-panel">
        {rebuild.error && <ErrorState error={rebuild.error} />}
        {rebuild.data && (
          <div className="notice">
            Reindexed {rebuild.data.indexed_unit_count} units into{" "}
            {rebuild.data.index_backend}.
          </div>
        )}
        <table className="data-table record-table">
          <thead>
            <tr>
              <th>State</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            <RecordRow label="backend" value={backend} />
            <RecordRow label="health" value={health} />
            <RecordRow
              label="active_unit_count"
              value={String(payload?.active_unit_count ?? "unknown")}
            />
            <RecordRow
              label="document_count"
              value={String(payload?.index_document_count ?? "unknown")}
            />
            <RecordRow
              label="unit_delta"
              value={String(payload?.index_unit_delta ?? "unknown")}
            />
            {Object.entries(index).map(([key, value]) => (
              <RecordRow
                key={key}
                label={key}
                value={typeof value === "object" ? jsonPreview(value) : String(value)}
              />
            ))}
          </tbody>
        </table>
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

function RecordRow({ label, value }: { label: string; value: string }) {
  return (
    <tr>
      <td>
        <strong>{label}</strong>
      </td>
      <td>{value}</td>
    </tr>
  );
}
