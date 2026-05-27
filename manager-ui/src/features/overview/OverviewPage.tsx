import { useQuery } from "@tanstack/react-query";
import { Activity, Database, FolderTree, MessagesSquare, PanelsTopLeft } from "lucide-react";

import { getStats } from "../../api/client";
import { Badge, ErrorState, LoadingState } from "../../components/Status";
import { formatNumber, formatTime } from "../../lib/format";

export function OverviewPage() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: getStats });

  if (stats.isLoading) return <LoadingState />;
  if (stats.error) return <ErrorState error={stats.error} />;

  const payload = stats.data;
  const topOwners = payload?.top_owners ?? [];
  const activeUnits = payload?.active_unit_count ?? 0;
  const totalUnits = payload?.unit_count ?? 0;
  const ownerCount = payload?.owner_count ?? 0;
  const namespaceCount = payload?.namespace_count ?? 0;
  const retentionDelta = totalUnits - activeUnits;
  const indexHealth = payload?.index_health ?? "unknown";

  return (
    <section className="page-stack">
      <header className="page-header memory-page-header">
        <div>
          <p className="eyebrow">Local control plane</p>
          <h1>Overview</h1>
        </div>
        <div className="header-actions">
          <Badge tone="good">online</Badge>
          <Badge tone={indexHealth === "synced" ? "good" : "warn"}>
            {indexHealth}
          </Badge>
        </div>
      </header>

      <section className="metric-hero">
        <div className="metric-hero-body">
          <p className="metric-hero-label">Active memory units</p>
          <p className="metric-hero-value">{formatNumber(activeUnits)}</p>
          <p className="metric-hero-sub">
            across <strong>{formatNumber(ownerCount)}</strong> owner
            {ownerCount === 1 ? "" : "s"} ·{" "}
            <strong>{formatNumber(namespaceCount)}</strong> namespace
            {namespaceCount === 1 ? "" : "s"}
            {retentionDelta > 0 ? (
              <>
                {" "}
                · <span className="metric-hero-mute">
                  {formatNumber(retentionDelta)} retained
                </span>
              </>
            ) : null}
          </p>
        </div>
        <div className="metric-hero-meta">
          <span className="metric-hero-meta-row">
            <FolderTree aria-hidden size={14} />
            {String(payload?.store ?? "unknown")} at{" "}
            <code>{String(payload?.path ?? "unknown")}</code>
          </span>
          <span className="metric-hero-meta-row">
            <Activity aria-hidden size={14} />
            Latest op {formatTime(payload?.latest_operation_at) || "—"}
          </span>
        </div>
      </section>

      <div className="metric-grid metric-grid-3">
        <Metric
          icon={<MessagesSquare aria-hidden size={16} />}
          label="Sessions"
          value={payload?.session_count}
          hint={`${formatNumber(payload?.dialogue_count)} dialogues`}
        />
        <Metric
          icon={<PanelsTopLeft aria-hidden size={16} />}
          label="Open windows"
          value={payload?.open_dialogue_window_count}
          hint={`${formatNumber(payload?.dialogue_window_count)} total windows`}
          tone={(payload?.open_dialogue_window_count ?? 0) > 0 ? "warn" : "muted"}
        />
        <Metric
          icon={<Database aria-hidden size={16} />}
          label="Indexed documents"
          value={payload?.index_document_count}
          hint={`${payload?.index_backend ?? "—"} · ${indexHealth}`}
          tone={indexHealth === "synced" ? "good" : "warn"}
        />
      </div>

      <div className="overview-grid">
        <section className="panel table-panel">
          <header className="panel-header">
            <h2>Storage</h2>
            <span className="panel-hint">
              schema {String(payload?.schema_version ?? "?")} /{" "}
              {String(payload?.latest_schema_version ?? "?")}
            </span>
          </header>
          <table className="data-table record-table">
            <tbody>
              <RecordRow
                label="Path"
                value={String(payload?.path ?? "unknown")}
                mono
              />
              <RecordRow
                label="File size"
                value={`${formatNumber(payload?.file_size_bytes)} bytes`}
              />
              <RecordRow
                label="Operation logs"
                value={formatNumber(payload?.operation_log_count)}
              />
              {(payload?.pending_schema_migration_count ?? 0) > 0 ? (
                <RecordRow
                  label="Pending migrations"
                  value={formatNumber(payload?.pending_schema_migration_count)}
                />
              ) : null}
            </tbody>
          </table>
        </section>

        <section className="panel table-panel">
          <header className="panel-header">
            <h2>Top namespaces</h2>
            <span className="panel-hint">{topOwners.length} group{topOwners.length === 1 ? "" : "s"}</span>
          </header>
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

function Metric({
  icon,
  label,
  value,
  hint,
  tone,
}: {
  icon?: React.ReactNode;
  label: string;
  value: unknown;
  hint?: string;
  tone?: "good" | "warn" | "muted";
}) {
  return (
    <div className={`metric metric-with-hint${tone ? ` metric-tone-${tone}` : ""}`}>
      <span className="metric-label">
        {icon}
        {label}
      </span>
      <strong>{formatNumber(value)}</strong>
      {hint ? <span className="metric-hint">{hint}</span> : null}
    </div>
  );
}

function RecordRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <tr>
      <td>
        <strong>{label}</strong>
      </td>
      <td className={mono ? "mono-cell" : undefined}>{value}</td>
    </tr>
  );
}
