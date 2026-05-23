import { useQuery } from "@tanstack/react-query";

import { getStats } from "../../api/client";
import { Badge, ErrorState, LoadingState } from "../../components/Status";
import { formatNumber, formatTime } from "../../lib/format";

export function OverviewPage() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: getStats });

  if (stats.isLoading) return <LoadingState />;
  if (stats.error) return <ErrorState error={stats.error} />;

  const payload = stats.data;
  const topOwners = payload?.top_owners ?? [];

  return (
    <section className="page-stack">
      <header className="page-header memory-page-header">
        <div>
          <p className="eyebrow">Local control plane</p>
          <h1>Overview</h1>
        </div>
        <div className="header-actions">
          <Badge tone="good">online</Badge>
          <Badge tone={payload?.index_health === "synced" ? "good" : "warn"}>
            {payload?.index_health ?? "unknown"}
          </Badge>
        </div>
      </header>

      <div className="results-strip">
        <div className="filter-chip-list">
          <span className="filter-hint">
            Store {String(payload?.store ?? "unknown")} at{" "}
            {String(payload?.path ?? "unknown")}
          </span>
        </div>
        <span className="result-count">
          Latest operation {formatTime(payload?.latest_operation_at)}
        </span>
      </div>

      <div className="metric-grid">
        <Metric label="Memory units" value={payload?.unit_count} />
        <Metric label="Active units" value={payload?.active_unit_count} />
        <Metric label="Dialogues" value={payload?.dialogue_count} />
        <Metric label="Index documents" value={payload?.index_document_count} />
      </div>

      <div className="overview-grid">
        <section className="panel table-panel">
          <table className="data-table record-table">
            <thead>
              <tr>
                <th>Storage</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              <RecordRow label="Path" value={String(payload?.path ?? "unknown")} />
              <RecordRow
                label="Schema"
                value={`${String(payload?.schema_version ?? "unknown")} / ${String(
                  payload?.latest_schema_version ?? "unknown",
                )}`}
              />
              <RecordRow
                label="File size"
                value={`${formatNumber(payload?.file_size_bytes)} bytes`}
              />
              <RecordRow
                label="Operation logs"
                value={formatNumber(payload?.operation_log_count)}
              />
            </tbody>
          </table>
        </section>

        <section className="panel table-panel">
          <table className="data-table namespace-table">
            <thead>
              <tr>
                <th>Owner</th>
                <th>Namespace</th>
                <th>Units</th>
              </tr>
            </thead>
            <tbody>
              {topOwners.length === 0 ? (
                <tr>
                  <td className="empty-table-cell" colSpan={3}>
                    No namespaces available.
                  </td>
                </tr>
              ) : (
                topOwners.map((item) => (
                  <tr key={`${item.owner_id}-${item.namespace}`}>
                    <td>
                      <div className="scope-cell">
                        <strong>{item.owner_id}</strong>
                      </div>
                    </td>
                    <td>{item.namespace ?? "default"}</td>
                    <td>{formatNumber(item.unit_count)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>
      </div>
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
