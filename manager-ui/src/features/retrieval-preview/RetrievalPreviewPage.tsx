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
        <section className="panel">
          <div className="result-header">
            <Badge>{preview.data.context.unit_count} units</Badge>
            <Badge>{preview.data.context.token_count} tokens</Badge>
          </div>
          <pre className="context-block">{preview.data.context.text}</pre>
          <ol className="ranked-list">
            {preview.data.ranked_units.map((item) => (
              <li key={item.unit.unit_id}>
                <strong>#{item.rank}</strong>
                <span>{item.score.toFixed(3)}</span>
                <p>{item.unit.text}</p>
              </li>
            ))}
          </ol>
        </section>
      )}
    </section>
  );
}
