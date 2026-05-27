import { FormEvent, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, Search, Sparkles } from "lucide-react";

import { getMemoryUnits, previewRetrieval } from "../../api/client";
import { Badge, EmptyState, ErrorState } from "../../components/Status";
import { TimeRangeFilter } from "../../components/TimeRangeFilter";
import { formatNumber, formatTime } from "../../lib/format";
import {
  localDateTimeToIso,
  nowDateTimeInputValue,
  timeRangePayload,
} from "../../lib/timeFilters";

export function RetrievalPreviewPage() {
  const [ownerId, setOwnerId] = useState("");
  const [namespaces, setNamespaces] = useState("");
  const [query, setQuery] = useState("");
  const [budget, setBudget] = useState("600");
  const [maxUnits, setMaxUnits] = useState("10");
  const [queryTime, setQueryTime] = useState(nowDateTimeInputValue());
  const [memoryRange, setMemoryRange] = useState({ start: "", end: "" });
  const preview = useMutation({ mutationFn: previewRetrieval });

  // Sample one stored memory unit to seed the form. The first unit's
  // owner/namespace + first few words of its text become an instant
  // "this is what a working query looks like" example.
  const sample = useQuery({
    queryKey: ["retrieval-preview-sample"],
    queryFn: () => getMemoryUnits({ limit: 1 }),
    staleTime: 30_000,
  });
  const seed = sample.data?.units?.[0];

  function applyExample() {
    if (!seed) return;
    setOwnerId(seed.scope.owner_id);
    setNamespaces(seed.scope.namespace ?? "");
    setQuery(seed.text.split(/[.!?\n]/)[0]?.slice(0, 80) ?? seed.text);
    setQueryTime(nowDateTimeInputValue());
    setMemoryRange({ start: "", end: "" });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const namespaceList = namespaces
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    preview.mutate({
      owner_id: ownerId,
      namespaces: namespaceList.length ? namespaceList : null,
      query,
      query_time: localDateTimeToIso(queryTime),
      time_range: timeRangePayload(memoryRange),
      max_units: Number(maxUnits),
      context_budget_tokens: Number(budget),
    });
  }

  return (
    <section className="page-stack">
      <header className="page-header memory-page-header">
        <div>
          <p className="eyebrow">Runtime parity</p>
          <h1>Retrieval Preview</h1>
        </div>
        <Badge tone="muted">read path</Badge>
      </header>

      <form className="filter-panel retrieval-filter-panel" onSubmit={submit}>
        <label>
          Owner
          <input
            placeholder="user-sim"
            value={ownerId}
            onChange={(event) => setOwnerId(event.target.value)}
            required
          />
        </label>
        <label>
          Namespaces
          <input
            placeholder="personal, work"
            value={namespaces}
            onChange={(event) => setNamespaces(event.target.value)}
          />
        </label>
        <label>
          Budget tokens
          <input value={budget} onChange={(event) => setBudget(event.target.value)} type="number" min="1" />
        </label>
        <label>
          Max units
          <input
            value={maxUnits}
            onChange={(event) => setMaxUnits(event.target.value)}
            type="number"
            min="1"
          />
        </label>
        <label>
          Query time
          <input
            inputMode="numeric"
            maxLength={16}
            pattern="\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}"
            placeholder="YYYY-MM-DDTHH:mm"
            title="YYYY-MM-DDTHH:mm"
            type="text"
            value={queryTime}
            onChange={(event) => setQueryTime(event.target.value)}
          />
        </label>
        <label className="retrieval-query-field">
          Query
          <textarea value={query} onChange={(event) => setQuery(event.target.value)} required />
        </label>
        <div className="filter-time retrieval-time-filter">
          <TimeRangeFilter compact value={memoryRange} onChange={setMemoryRange} />
        </div>
        <div className="filter-actions">
          {seed ? (
            <button
              type="button"
              className="ghost-button"
              onClick={applyExample}
              title={`Prefill from ${seed.scope.owner_id}${seed.scope.namespace ? "/" + seed.scope.namespace : ""}`}
            >
              <span className="button-content">
                <Sparkles aria-hidden="true" size={14} />
                Use example
              </span>
            </button>
          ) : null}
          <button type="submit" disabled={preview.isPending}>
            <span className="button-content">
              {preview.isPending ? (
                <Loader2 aria-hidden="true" className="loading-spinner" size={16} />
              ) : (
                <Search aria-hidden="true" size={16} />
              )}
              {preview.isPending ? "Running" : "Run preview"}
            </span>
          </button>
        </div>
      </form>

      <div className="results-strip">
        <div className="filter-chip-list">
          <span className="filter-hint">
            Preview uses the same ranking and render budget as agent reads.
          </span>
        </div>
        <span className="result-count">
          {budget} tokens / {maxUnits} units
        </span>
      </div>

      {preview.error && <ErrorState error={preview.error} />}
      {preview.data && (
        <section className="page-stack">
          <div className="results-strip">
            <div className="filter-chip-list">
              {previewSummaryItems(ownerId, namespaces, memoryRange).map((item) => (
                <span className="filter-chip static-chip" key={item}>
                  {item}
                </span>
              ))}
            </div>
            <span className="result-count">
              Rendered {preview.data.context.unit_count} of{" "}
              {preview.data.ranked_units.length} ranked
            </span>
          </div>

          <div className="metric-grid">
            <Metric label="Candidates" value={preview.data.stats.candidate_count} />
            <Metric label="Ranked" value={preview.data.stats.ranked_count} />
            <Metric label="Rendered" value={preview.data.context.unit_count} />
            <Metric
              label="Skipped"
              value={preview.data.stats.skipped_due_to_budget_count}
            />
          </div>

          <section className="panel table-panel">
            {preview.data.ranked_units.length === 0 ? (
              <EmptyState message="No memory units matched the preview query." />
            ) : (
              <table className="data-table ranked-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Memory</th>
                    <th>Scope</th>
                    <th>Score</th>
                    <th>Tokens</th>
                    <th>State</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.data.ranked_units.map((item) => {
                    const rendered = preview.data?.stats.rendered_unit_ids?.includes(
                      item.unit.unit_id,
                    );
                    const tokenEstimate =
                      preview.data?.stats.ranked_token_estimates?.find(
                        (estimate) => estimate.unit_id === item.unit.unit_id,
                      )?.render_line_tokens ?? "unknown";
                    return (
                      <tr key={item.unit.unit_id}>
                        <td>#{item.rank}</td>
                        <td>
                          <div className="memory-cell">
                            <a
                              className="memory-link"
                              href={`#/memory-units/${encodeURIComponent(
                                item.unit.unit_id,
                              )}`}
                              title={item.unit.text}
                            >
                              {item.unit.text}
                            </a>
                            <span className="memory-id">
                              {formatTime(item.unit.timestamp)}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="scope-cell">
                            <strong>{item.unit.scope.owner_id}</strong>
                            <span>{item.unit.scope.namespace ?? "default"}</span>
                          </div>
                        </td>
                        <td>{item.score.toFixed(3)}</td>
                        <td>{tokenEstimate}</td>
                        <td>
                          <Badge tone={rendered ? "good" : "warn"}>
                            {rendered ? "rendered" : "skipped"}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </section>

          <section className="panel context-panel">
            <div className="result-header">
              <div>
                <h2>Rendered Context</h2>
                <p className="muted-line">
                  {preview.data.context.unit_count} units,{" "}
                  {preview.data.context.token_count} tokens
                </p>
              </div>
              <Badge>
                budget {preview.data.stats.context_budget_tokens ?? "none"}
              </Badge>
            </div>
            <pre className="context-block">{preview.data.context.text}</pre>
          </section>
        </section>
      )}
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

function previewSummaryItems(
  ownerId: string,
  namespaces: string,
  memoryRange: { start: string; end: string },
) {
  const items = [`Owner: ${ownerId}`];
  if (namespaces.trim()) items.push(`Namespaces: ${namespaces}`);
  if (memoryRange.start || memoryRange.end) {
    items.push(`${memoryRange.start || "Any start"} to ${memoryRange.end || "Any end"}`);
  } else {
    items.push("All memory time");
  }
  return items;
}
