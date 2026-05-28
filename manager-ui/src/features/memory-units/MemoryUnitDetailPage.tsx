import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";

import { getMemoryUnit } from "../../api/client";
import type { SourceChunk } from "../../api/types";
import { CopyableId } from "../../components/CopyableId";
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

      <section className="panel fact-panel">
        <div className="fact-card-header">
          <div>
            <p className="eyebrow">Processed Fact</p>
            <h2>{unit.memory_type}</h2>
          </div>
          <div className="fact-card-meta">
            <CopyableId value={unit.unit_id} />
            <Badge tone={unit.redacted_at ? "warn" : "good"}>
              {unit.redacted_at ? "redacted" : "active"}
            </Badge>
          </div>
        </div>
        <p className="fact-text">{unit.text}</p>
        <div className="fact-meta-grid">
          <span>
            <strong>Owner</strong>
            {unit.scope.owner_id}
          </span>
          <span>
            <strong>Namespace</strong>
            {unit.scope.namespace ?? "default"}
          </span>
          <span>
            <strong>Available at</strong>
            {formatTime(unit.available_at)}
          </span>
          <span>
            <strong>Source</strong>
            {sourceChunks.length} {sourceChunks.length === 1 ? "dialogue" : "dialogues"}
          </span>
          {unit.retention_until ? (
            <span>
              <strong>Retention until</strong>
              {formatTime(unit.retention_until)}
            </span>
          ) : null}
          {unit.redacted_at ? (
            <span>
              <strong>Redacted at</strong>
              {formatTime(unit.redacted_at)}
            </span>
          ) : null}
        </div>
      </section>

      <section className="panel">
        <h2>Source Dialogue</h2>
        <div className="source-stack">
          {sourceChunks.map((chunk, index) => (
            <article className="source-block" key={`${chunk.range_label}-${index}`}>
              <div className="source-header">
                <SourceDialogueHeader chunk={chunk} />
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

      {Object.keys(unit.metadata).length > 0 ? (
        <section className="panel">
          <h2>Metadata</h2>
          <pre className="json-block">{jsonPreview(unit.metadata)}</pre>
        </section>
      ) : null}
    </section>
  );
}

function SourceDialogueHeader({ chunk }: { chunk: SourceChunk }) {
  const dialogueId = chunk.dialogue?.dialogue_id ?? "missing dialogue";
  const sessionId = chunk.dialogue?.session_id;
  return (
    <div className="source-dialogue-meta">
      <div className="source-meta-item">
        <strong>Status</strong>
        <Badge tone={chunk.status === "ok" ? "good" : "warn"}>{chunk.status}</Badge>
      </div>
      <div className="source-meta-item">
        <strong>Session</strong>
        {sessionId && chunk.dialogue ? (
          <a
            className="mono-link"
            href={sourceDialogueHref(sessionId, chunk.dialogue.dialogue_id)}
          >
            {sessionId}
          </a>
        ) : (
          <span>none</span>
        )}
      </div>
      <div className="source-meta-item source-meta-dialogue">
        <strong>Dialogue</strong>
        <span className="mono-text">{dialogueId}</span>
      </div>
      <div className="source-meta-item">
        <strong>Evidence</strong>
        <Badge tone={chunk.ref.message_range ? "neutral" : "muted"}>
          {chunk.range_label}
        </Badge>
      </div>
    </div>
  );
}

function sourceDialogueHref(sessionId: string, dialogueId: string) {
  const query = new URLSearchParams({ dialogue_id: dialogueId });
  return `#/sessions/${encodeURIComponent(sessionId)}?${query.toString()}`;
}
