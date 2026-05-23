import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { previewRetrieval } from "../../api/client";
import { Badge, ErrorState } from "../../components/Status";

export function RetrievalPreviewPage() {
  const [ownerId, setOwnerId] = useState("");
  const [namespaces, setNamespaces] = useState("");
  const [query, setQuery] = useState("");
  const [budget, setBudget] = useState("600");
  const preview = useMutation({ mutationFn: previewRetrieval });

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
      query_time: new Date().toISOString(),
      max_units: 10,
      context_budget_tokens: Number(budget),
    });
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Runtime parity</p>
          <h1>Retrieval Preview</h1>
        </div>
      </header>

      <form className="panel form-grid" onSubmit={submit}>
        <label>
          Owner
          <input value={ownerId} onChange={(event) => setOwnerId(event.target.value)} required />
        </label>
        <label>
          Namespaces
          <input value={namespaces} onChange={(event) => setNamespaces(event.target.value)} />
        </label>
        <label>
          Budget
          <input value={budget} onChange={(event) => setBudget(event.target.value)} type="number" min="1" />
        </label>
        <label className="form-wide">
          Query
          <textarea value={query} onChange={(event) => setQuery(event.target.value)} required />
        </label>
        <button type="submit" disabled={preview.isPending}>
          {preview.isPending ? "Running..." : "Run preview"}
        </button>
      </form>

      {preview.error && <ErrorState error={preview.error} />}
      {preview.data && (
        <section className="page-stack">
          <div className="metric-grid">
            <Metric label="Candidates" value={preview.data.stats.candidate_count} />
            <Metric label="Ranked" value={preview.data.stats.ranked_count} />
            <Metric label="Rendered" value={preview.data.context.unit_count} />
            <Metric
              label="Skipped"
              value={preview.data.stats.skipped_due_to_budget_count}
            />
          </div>

          <section className="panel">
            <div className="result-header">
              <Badge>{preview.data.context.unit_count} rendered</Badge>
              <Badge>{preview.data.context.token_count} tokens</Badge>
              <Badge>
                budget {preview.data.stats.context_budget_tokens ?? "none"}
              </Badge>
            </div>
            <pre className="context-block">{preview.data.context.text}</pre>
          </section>

          <section className="panel table-panel">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>State</th>
                  <th>Score</th>
                  <th>Tokens</th>
                  <th>Memory</th>
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
                        <Badge tone={rendered ? "good" : "warn"}>
                          {rendered ? "rendered" : "skipped"}
                        </Badge>
                      </td>
                      <td>{item.score.toFixed(3)}</td>
                      <td>{tokenEstimate}</td>
                      <td>{item.unit.text}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
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
      <strong>{String(value ?? "0")}</strong>
    </div>
  );
}
