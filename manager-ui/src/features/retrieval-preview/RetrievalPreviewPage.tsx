import {
  FormEvent,
  KeyboardEvent,
  useMemo,
  useRef,
  useState,
} from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, ClipboardCopy, Loader2, Search, Sparkles } from "lucide-react";

import { getMemoryUnits, previewRetrieval } from "../../api/client";
import { MemoryUnit } from "../../api/types";
import { Badge, EmptyState, ErrorState } from "../../components/Status";
import { TimeRangeFilter } from "../../components/TimeRangeFilter";
import { formatNumber, formatTime } from "../../lib/format";
import {
  localDateTimeToIso,
  nowDateTimeInputValue,
  timeRangePayload,
} from "../../lib/timeFilters";

type TimeRangeInput = { start: string; end: string };

export function RetrievalPreviewPage() {
  const [ownerId, setOwnerId] = useState("");
  const [namespaces, setNamespaces] = useState("");
  const [query, setQuery] = useState("");
  const [budget, setBudget] = useState("600");
  const [maxUnits, setMaxUnits] = useState("10");
  const [queryTime, setQueryTime] = useState(nowDateTimeInputValue());
  const [memoryRange, setMemoryRange] = useState<TimeRangeInput>({ start: "", end: "" });
  const [contextCopied, setContextCopied] = useState(false);
  const preview = useMutation({ mutationFn: previewRetrieval });
  const formRef = useRef<HTMLFormElement | null>(null);

  // Sample a handful of stored units, then dedupe by owner+namespace so
  // example chips cover distinct scopes — gives a first-run user real
  // queries they can run against actual data with one click.
  const sample = useQuery({
    queryKey: ["retrieval-preview-examples"],
    queryFn: () => getMemoryUnits({ limit: 8 }),
    staleTime: 30_000,
  });
  const examples = useMemo<MemoryUnit[]>(() => {
    const seen = new Set<string>();
    const out: MemoryUnit[] = [];
    for (const unit of sample.data?.units ?? []) {
      const key = `${unit.scope.owner_id}/${unit.scope.namespace ?? ""}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(unit);
      if (out.length >= 3) break;
    }
    return out;
  }, [sample.data]);
  const seed = examples[0] ?? null;

  function runPreview(payload: {
    owner_id: string;
    namespace: string | null;
    query: string;
    time: TimeRangeInput;
    queryTime: string;
  }) {
    preview.mutate({
      owner_id: payload.owner_id,
      namespaces: payload.namespace ? [payload.namespace] : null,
      query: payload.query,
      query_time: localDateTimeToIso(payload.queryTime),
      time_range: timeRangePayload(payload.time),
      max_units: Number(maxUnits),
      context_budget_tokens: Number(budget),
    });
  }

  function applyExample(unit: MemoryUnit, autoRun: boolean) {
    const sampleQuery = unit.text.split(/[.!?\n]/)[0]?.slice(0, 80) ?? unit.text;
    const nowValue = nowDateTimeInputValue();
    setOwnerId(unit.scope.owner_id);
    setNamespaces(unit.scope.namespace ?? "");
    setQuery(sampleQuery);
    setQueryTime(nowValue);
    setMemoryRange({ start: "", end: "" });
    if (autoRun) {
      runPreview({
        owner_id: unit.scope.owner_id,
        namespace: unit.scope.namespace ?? null,
        query: sampleQuery,
        time: { start: "", end: "" },
        queryTime: nowValue,
      });
    }
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

  function handleQueryKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  }

  async function copyContext() {
    const text = preview.data?.context.text;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setContextCopied(true);
      window.setTimeout(() => setContextCopied(false), 1100);
    } catch {
      /* clipboard not available */
    }
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

      <form
        className="filter-panel retrieval-form"
        onSubmit={submit}
        ref={formRef}
      >
        <div className="retrieval-row retrieval-row-primary">
          <label className="retrieval-field-owner">
            Owner
            <input
              placeholder="user-sim"
              value={ownerId}
              onChange={(event) => setOwnerId(event.target.value)}
              required
            />
          </label>
          <label className="retrieval-field-ns">
            Namespaces
            <input
              placeholder="personal, work"
              value={namespaces}
              onChange={(event) => setNamespaces(event.target.value)}
            />
          </label>
          <div className="retrieval-actions">
            {seed ? (
              <button
                type="button"
                className="ghost-button"
                onClick={() => applyExample(seed, false)}
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
        </div>

        <label className="retrieval-field-query">
          Query
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleQueryKeyDown}
            placeholder="What do you want to retrieve about this owner? (⌘/Ctrl + Enter to run)"
            required
          />
        </label>

        <details className="retrieval-tuning">
          <summary>
            <span className="retrieval-tuning-label">Tuning</span>
            <span className="retrieval-tuning-summary">
              {budget} tokens · {maxUnits} units · {queryTime || "now"} · {summarizeRange(memoryRange)}
            </span>
          </summary>
          <div className="retrieval-tuning-grid">
            <label>
              Budget tokens
              <input
                value={budget}
                onChange={(event) => setBudget(event.target.value)}
                type="number"
                min="1"
              />
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
                placeholder="YYYY-MM-DDTHH:mm"
                title="YYYY-MM-DDTHH:mm"
                type="text"
                value={queryTime}
                onChange={(event) => setQueryTime(event.target.value)}
              />
            </label>
            <div className="retrieval-tuning-time">
              <TimeRangeFilter compact value={memoryRange} onChange={setMemoryRange} />
            </div>
          </div>
        </details>
      </form>

      {!preview.data && !preview.error && examples.length > 0 ? (
        <section className="panel retrieval-empty">
          <div className="retrieval-empty-head">
            <h2>Try a query</h2>
            <p className="muted-line">
              Click an example below to prefill and run — same ranking and render budget
              the agent sees.
            </p>
          </div>
          <div className="retrieval-example-grid">
            {examples.map((unit) => (
              <button
                type="button"
                className="retrieval-example-chip"
                key={unit.unit_id}
                onClick={() => applyExample(unit, true)}
              >
                <span className="retrieval-example-scope">
                  {unit.scope.owner_id}
                  {unit.scope.namespace ? <em>/{unit.scope.namespace}</em> : null}
                </span>
                <span className="retrieval-example-text">
                  {truncateText(unit.text, 96)}
                </span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

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
                    <th>Score</th>
                    <th>Tokens</th>
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
                      )?.render_line_tokens ?? null;
                    const parts = pickScoreParts(item.score_breakdown);
                    return (
                      <tr
                        className={
                          rendered ? "ranked-row-kept" : "ranked-row-cut"
                        }
                        key={item.unit.unit_id}
                      >
                        <td>
                          <span className="rank-marker">#{item.rank}</span>
                        </td>
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
                              {item.unit.scope.namespace ? (
                                <span className="memory-cell-ns">
                                  · {item.unit.scope.namespace}
                                </span>
                              ) : null}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="score-cell">
                            <strong>{item.score.toFixed(3)}</strong>
                            {parts ? (
                              <span className="score-parts">
                                {parts.relevance !== null ? (
                                  <span title="relevance">
                                    <em>R</em>
                                    {parts.relevance.toFixed(2)}
                                  </span>
                                ) : null}
                                {parts.recency !== null ? (
                                  <span title="recency">
                                    <em>T</em>
                                    {parts.recency.toFixed(2)}
                                  </span>
                                ) : null}
                              </span>
                            ) : null}
                          </div>
                        </td>
                        <td>
                          <span className="token-cell">
                            {tokenEstimate ?? "—"}
                            {rendered ? null : (
                              <span
                                className="token-cell-hint"
                                title="Not rendered — ranked but budget exhausted"
                              >
                                cut
                              </span>
                            )}
                          </span>
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
              <div className="context-panel-actions">
                <Badge>
                  budget {preview.data.stats.context_budget_tokens ?? "none"}
                </Badge>
                <button
                  type="button"
                  className="ghost-button"
                  onClick={copyContext}
                  disabled={!preview.data.context.text}
                  title="Copy rendered context"
                >
                  <span className="button-content">
                    {contextCopied ? (
                      <Check aria-hidden="true" size={14} />
                    ) : (
                      <ClipboardCopy aria-hidden="true" size={14} />
                    )}
                    {contextCopied ? "Copied" : "Copy"}
                  </span>
                </button>
              </div>
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
  memoryRange: TimeRangeInput,
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

function summarizeRange(range: TimeRangeInput) {
  if (!range.start && !range.end) return "all time";
  if (range.start && range.end) return `${range.start} → ${range.end}`;
  if (range.start) return `since ${range.start}`;
  return `until ${range.end}`;
}

function truncateText(value: string, max: number) {
  const trimmed = value.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max - 1).trimEnd()}…`;
}

function pickScoreParts(breakdown: Record<string, unknown> | undefined) {
  if (!breakdown) return null;
  const relevance = typeof breakdown.relevance === "number" ? breakdown.relevance : null;
  const recency = typeof breakdown.recency === "number" ? breakdown.recency : null;
  if (relevance === null && recency === null) return null;
  return { relevance, recency };
}
