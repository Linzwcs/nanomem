import { useQuery } from "@tanstack/react-query";

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
      <header className="page-header">
        <div>
          <a className="back-link" href={backHref}>Memory Units</a>
          <h1>{unit.memory_type}</h1>
        </div>
        <Badge tone={unit.redacted_at ? "warn" : "good"}>
          {unit.redacted_at ? "redacted" : "active"}
        </Badge>
      </header>

      <section className="panel">
        <p className="fact-text">{unit.text}</p>
        <dl className="definition-grid">
          <dt>Unit id</dt>
          <dd>{unit.unit_id}</dd>
          <dt>Owner</dt>
          <dd>{unit.scope.owner_id}</dd>
          <dt>Namespace</dt>
          <dd>{unit.scope.namespace ?? "none"}</dd>
          <dt>Timestamp</dt>
          <dd>{formatTime(unit.timestamp)}</dd>
          <dt>Confidence</dt>
          <dd>{unit.confidence?.toFixed(2) ?? "none"}</dd>
        </dl>
      </section>

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
                    className={message.in_ref_range ? "message-in-range" : ""}
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
