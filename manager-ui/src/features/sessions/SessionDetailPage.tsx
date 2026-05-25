import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";

import { getSession } from "../../api/client";
import type { DialogueWindow, SessionStreamMessage } from "../../api/types";
import { Badge, ErrorState, LoadingState } from "../../components/Status";
import { formatNumber, formatTime, jsonPreview } from "../../lib/format";

export function SessionDetailPage({
  dialogueId,
  sessionId,
}: {
  dialogueId: string | null;
  sessionId: string;
}) {
  const detail = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => getSession(sessionId),
  });

  if (detail.isLoading) return <LoadingState />;
  if (detail.error) return <ErrorState error={detail.error} />;
  if (!detail.data) return null;

  const { session, messages, windows, produced_units: producedUnits } = detail.data;
  const targetWindow = dialogueId
    ? windows.find((window) => window.dialogue_id === dialogueId)
    : null;
  const targetFound = dialogueId ? Boolean(targetWindow) : false;

  return (
    <section className="page-stack">
      <header className="page-header memory-page-header">
        <div>
          <a className="back-link" href="#/sessions">
            <ArrowLeft aria-hidden="true" size={15} />
            Sessions
          </a>
          <h1>Session Stream</h1>
        </div>
        <div className="header-actions">
          <Badge tone={session.window_counts.open ? "warn" : "good"}>
            {session.window_counts.open ? "buffering" : "settled"}
          </Badge>
          <Badge>{formatNumber(messages.length)} messages</Badge>
        </div>
      </header>

      <div className="results-strip">
        <div className="filter-chip-list">
          <span className="filter-chip static-chip">Session: {session.session_id}</span>
          <span className="filter-chip static-chip">
            Windows: {formatNumber(session.window_count)}
          </span>
          <span className="filter-chip static-chip">
            Units: {formatNumber(session.produced_unit_count)}
          </span>
          {dialogueId ? (
            <span className="filter-chip static-chip">
              Source dialogue: {targetFound ? dialogueId : "not found"}
            </span>
          ) : null}
        </div>
        <span className="result-count">Updated {formatTime(session.updated_at)}</span>
      </div>

      {dialogueId ? (
        <div className={targetFound ? "notice" : "notice notice-warn"}>
          {targetFound
            ? "Source dialogue is highlighted in the message stream."
            : "The requested source dialogue was not found in this session."}
        </div>
      ) : null}

      <div className="metric-grid">
        <Metric label="Messages" value={messages.length} />
        <Metric label="Windows" value={windows.length} />
        <Metric label="Produced units" value={producedUnits.length} />
        <Metric label="Dialogues" value={session.dialogue_count} />
      </div>

      <section className="panel table-panel">
        <table className="data-table window-table">
          <thead>
            <tr>
              <th>Window</th>
              <th>Status</th>
              <th>Messages</th>
              <th>Tokens</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {windows.map((window) => (
              <WindowRow
                highlighted={window.dialogue_id === dialogueId}
                key={window.dialogue_id}
                window={window}
              />
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Message Stream</h2>
          <Badge tone="muted">chronological evidence</Badge>
        </div>
        <ol className="dialogue-log stream-log">
          {messages.map((message) => (
            <StreamMessage
              highlightedDialogueId={dialogueId}
              key={`${message.dialogue_id}-${message.local_index}`}
              message={message}
            />
          ))}
        </ol>
      </section>

      <section className="panel table-panel">
        <table className="data-table memory-table">
          <thead>
            <tr>
              <th>Produced Memory</th>
              <th>Scope</th>
              <th>Type</th>
              <th>Source</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {producedUnits.length === 0 ? (
              <tr>
                <td className="empty-table-cell" colSpan={5}>
                  No memory units have been produced for this session.
                </td>
              </tr>
            ) : (
              producedUnits.map((unit) => (
                <tr key={unit.unit_id}>
                  <td>
                    <a
                      className="memory-link"
                      href={`#/memory-units/${encodeURIComponent(unit.unit_id)}`}
                    >
                      {unit.text}
                    </a>
                    <span className="memory-id">{unit.unit_id}</span>
                  </td>
                  <td>
                    <div className="scope-cell">
                      <strong>{unit.scope.owner_id}</strong>
                      <span>{unit.scope.namespace ?? "default"}</span>
                    </div>
                  </td>
                  <td>
                    <Badge>{unit.memory_type}</Badge>
                  </td>
                  <td>{unit.dialogue_refs.length} refs</td>
                  <td>{formatTime(unit.timestamp)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <h2>Metadata</h2>
        <pre className="json-block">{jsonPreview(session.metadata)}</pre>
      </section>
    </section>
  );
}

function WindowRow({
  highlighted,
  window,
}: {
  highlighted: boolean;
  window: DialogueWindow;
}) {
  return (
    <tr className={highlighted ? "dialogue-row-highlighted" : ""}>
      <td>
        <div className="scope-cell">
          <a
            className="memory-link mono-link"
            href={`#/dialogue-windows?session_id=${encodeURIComponent(
              window.session_id,
            )}`}
          >
            {window.dialogue_id}
          </a>
          <span>{window.seal_reason ?? "active chunk"}</span>
        </div>
      </td>
      <td>
        <Badge tone={statusTone(window.status)}>{window.status}</Badge>
      </td>
      <td>{formatNumber(window.message_count)}</td>
      <td>{formatNumber(window.token_count)}</td>
      <td>{formatTime(window.updated_at)}</td>
    </tr>
  );
}

function StreamMessage({
  highlightedDialogueId,
  message,
}: {
  highlightedDialogueId: string | null;
  message: SessionStreamMessage;
}) {
  const dialogueHighlighted = message.dialogue_id === highlightedDialogueId;
  return (
    <li
      className={[
        dialogueHighlighted ? "dialogue-chunk-highlighted" : "",
        message.produced_unit_ids.length ? "message-in-range" : "",
        `message-role-${message.role}`,
      ].join(" ")}
    >
      <div className="message-meta">
        <span>#{message.index}</span>
        <strong>{message.speaker_id ?? message.role}</strong>
        <time>{formatTime(message.timestamp)}</time>
        {message.window_status && (
          <Badge tone={statusTone(message.window_status)}>
            {message.window_status}
          </Badge>
        )}
      </div>
      <p>{message.content}</p>
      <div className="message-meta">
        <span>{message.dialogue_id}</span>
        <span>chunk index {message.local_index}</span>
        {message.window_seal_reason && <span>{message.window_seal_reason}</span>}
      </div>
    </li>
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

function statusTone(status: string): "neutral" | "good" | "warn" | "muted" {
  if (status === "open") return "warn";
  if (status === "extracted") return "good";
  if (status === "failed") return "warn";
  return "muted";
}
