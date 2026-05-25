import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { getDialogueWindows } from "../../api/client";
import { Badge, EmptyState, ErrorState, LoadingState } from "../../components/Status";
import { formatNumber, formatTime } from "../../lib/format";

export function DialogueWindowsPage() {
  const filters = windowFiltersFromHash();
  const limit = numberParam(filters.limit, 50);
  const page = numberParam(filters.page, 1);

  const windows = useQuery({
    queryKey: ["dialogue-windows", filters],
    queryFn: () =>
      getDialogueWindows({
        session_id: filters.session_id,
        status: filters.status,
        order: filters.order,
        page,
        limit,
      }),
  });

  if (windows.isLoading) return <LoadingState />;
  if (windows.error) return <ErrorState error={windows.error} />;

  const rows = windows.data?.windows ?? [];

  return (
    <section className="page-stack">
      <header className="page-header memory-page-header">
        <div>
          <p className="eyebrow">Extraction lifecycle</p>
          <h1>Dialogue Windows</h1>
        </div>
        <Badge>{windows.data?.total_count ?? 0} total</Badge>
      </header>

      <section className="filter-panel window-filter-panel">
        <label>
          Session
          <input
            placeholder="session id"
            value={filters.session_id}
            onChange={(event) => updateWindowFilter("session_id", event.target.value)}
          />
        </label>
        <label>
          Status
          <select
            value={filters.status}
            onChange={(event) => updateWindowFilter("status", event.target.value)}
          >
            <option value="">Any</option>
            <option value="open">Open</option>
            <option value="sealed">Sealed</option>
            <option value="extracting">Extracting</option>
            <option value="extracted">Extracted</option>
            <option value="failed">Failed</option>
          </select>
        </label>
        <label>
          Order
          <select
            value={filters.order}
            onChange={(event) => updateWindowFilter("order", event.target.value)}
          >
            <option value="newest_first">Recently updated</option>
            <option value="oldest_first">Oldest updated</option>
          </select>
        </label>
        <label>
          Rows
          <select
            value={filters.limit}
            onChange={(event) => updateWindowFilter("limit", event.target.value)}
          >
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </label>
        <div className="filter-actions">
          <button
            className="ghost-button"
            onClick={() => {
              window.location.hash = "#/dialogue-windows";
            }}
            type="button"
          >
            Clear
          </button>
        </div>
      </section>

      <section className="panel table-panel">
        {rows.length === 0 ? (
          <EmptyState message="No dialogue windows match the current filters." />
        ) : (
          <table className="data-table window-table">
            <thead>
              <tr>
                <th>Dialogue Window</th>
                <th>Session</th>
                <th>Status</th>
                <th>Messages</th>
                <th>Tokens</th>
                <th>Units</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((window) => (
                <tr key={window.dialogue_id}>
                  <td>
                    <div className="scope-cell">
                      <strong className="mono-text">{window.dialogue_id}</strong>
                      <span>{window.seal_reason ?? "active chunk"}</span>
                    </div>
                  </td>
                  <td>
                    <a
                      className="memory-link mono-link"
                      href={`#/sessions/${encodeURIComponent(window.session_id)}`}
                    >
                      {window.session_id}
                    </a>
                  </td>
                  <td>
                    <Badge tone={statusTone(window.status)}>{window.status}</Badge>
                  </td>
                  <td>{formatNumber(window.message_count)}</td>
                  <td>{formatNumber(window.token_count)}</td>
                  <td>{formatNumber(window.produced_unit_count)}</td>
                  <td>{formatTime(window.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <div className="pagination-bar">
        <span>
          Showing {windows.data?.offset ?? 0}-
          {(windows.data?.offset ?? 0) + (windows.data?.count ?? 0)} of{" "}
          {windows.data?.total_count ?? 0}
        </span>
        <div>
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => updateWindowFilter("page", String(page - 1))}
          >
            <span className="button-content">
              <ChevronLeft aria-hidden="true" size={16} />
              Previous
            </span>
          </button>
          <button
            type="button"
            disabled={!windows.data?.has_more}
            onClick={() => updateWindowFilter("page", String(page + 1))}
          >
            <span className="button-content">
              Next
              <ChevronRight aria-hidden="true" size={16} />
            </span>
          </button>
        </div>
      </div>
    </section>
  );
}

type WindowFilters = {
  session_id: string;
  status: string;
  order: string;
  page: string;
  limit: string;
};

function windowFiltersFromHash(): WindowFilters {
  const query = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  return {
    session_id: query.get("session_id") ?? "",
    status: query.get("status") ?? "",
    order: query.get("order") ?? "newest_first",
    page: query.get("page") ?? "1",
    limit: query.get("limit") ?? "50",
  };
}

function updateWindowFilter(key: keyof WindowFilters, value: string) {
  const filters = { ...windowFiltersFromHash(), [key]: value, page: "1" };
  if (key === "page") filters.page = value;
  const query = new URLSearchParams();
  for (const [filterKey, filterValue] of Object.entries(filters)) {
    if (
      filterValue &&
      !(filterKey === "page" && filterValue === "1") &&
      !(filterKey === "order" && filterValue === "newest_first") &&
      !(filterKey === "limit" && filterValue === "50")
    ) {
      query.set(filterKey, filterValue);
    }
  }
  const encoded = query.toString();
  window.location.hash = encoded
    ? `#/dialogue-windows?${encoded}`
    : "#/dialogue-windows";
}

function numberParam(value: string, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function statusTone(status: string): "neutral" | "good" | "warn" | "muted" {
  if (status === "open") return "warn";
  if (status === "extracted") return "good";
  if (status === "failed") return "warn";
  return "muted";
}
