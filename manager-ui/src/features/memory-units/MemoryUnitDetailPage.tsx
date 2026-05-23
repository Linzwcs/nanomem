import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";

import { getMemoryUnit } from "../../api/client";
import { Badge, ErrorState, LoadingState } from "../../components/Status";
import { formatTime, jsonPreview } from "../../lib/format";

export function MemoryUnitDetailPage({ unitId }: { unitId: string }) {
  const detail = useQuery({
    queryKey: ["memory-unit", unitId],
    queryFn: () => getMemoryUnit(unitId),
  });

  if (detail.isLoading) return <LoadingState />;
  if (detail.error) return <ErrorState error={detail.error} />;
  if (!detail.data) return null;

  const { unit, source_chunks: sourceChunks } = detail.data;
  const backHref =
    sessionStorage.getItem("nanomem.memoryUnitsHash") || "#/memory-units";

  return (
    <section className="page-stack">
      <header className="page-header memory-page-header">
        <div>
          <a className="back-link" href={backHref}>
            <ArrowLeft aria-hidden="true" size={15} />
            Memory Units
          </a>
          <h1>Memory Unit</h1>
        </div>
        <Badge tone={unit.redacted_at ? "warn" : "good"}>
          {unit.redacted_at ? "redacted" : "active"}
        </Badge>
      </header>

      <div className="results-strip">
        <div className="filter-chip-list">
          <span className="filter-chip static-chip">Type: {unit.memory_type}</span>
          <span className="filter-chip static-chip">Owner: {unit.scope.owner_id}</span>
          <span className="filter-chip static-chip">
            Namespace: {unit.scope.namespace ?? "default"}
          </span>
        </div>
        <span className="result-count">{formatTime(unit.timestamp)}</span>
      </div>

      <div className="detail-grid">
        <section className="panel fact-panel">
          <p className="fact-text">{unit.text}</p>
          <div className="fact-badges">
            <Badge>{unit.memory_type}</Badge>
            <Badge tone="muted">{unit.scope.namespace ?? "default"}</Badge>
          </div>
        </section>

        <section className="panel table-panel">
          <table className="data-table record-table">
            <thead>
              <tr>
                <th>Record</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              <RecordRow label="Unit id" value={unit.unit_id} />
              <RecordRow label="Owner" value={unit.scope.owner_id} />
              <RecordRow
                label="Namespace"
                value={unit.scope.namespace ?? "default"}
              />
              <RecordRow label="Timestamp" value={formatTime(unit.timestamp)} />
            </tbody>
          </table>
        </section>
      </div>

      <section className="panel">
        <h2>Source Dialogue</h2>
        <div className="source-stack">
          {sourceChunks.map((chunk, index) => (
            <article className="source-block" key={`${chunk.range_label}-${index}`}>
              <div className="source-header">
                <Badge tone={chunk.status === "ok" ? "good" : "warn"}>
                  {chunk.status}
                </Badge>
                <span>{chunk.range_label}</span>
                <span>{chunk.dialogue?.dialogue_id ?? "missing dialogue"}</span>
              </div>
              <ol className="dialogue-log">
                {(chunk.dialogue_messages ?? chunk.messages).map((message) => (
                  <li
                    className={[
                      message.in_ref_range ? "message-in-range" : "",
                      `message-role-${message.role}`,
                    ].join(" ")}
                    key={`${message.index}-${message.timestamp}`}
                  >
                    <div className="message-meta">
                      <span>{message.index ?? "-"}</span>
                      <strong>{message.speaker_id ?? message.role}</strong>
                      <time>{formatTime(message.timestamp)}</time>
                    </div>
                    <p>{message.content}</p>
                  </li>
                ))}
              </ol>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Metadata</h2>
        <pre className="json-block">{jsonPreview(unit.metadata)}</pre>
      </section>
    </section>
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
