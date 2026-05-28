import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { getSessions } from "../../api/client";
import { Badge, EmptyState, ErrorState, LoadingState } from "../../components/Status";
import { formatNumber, formatTime } from "../../lib/format";

export function SessionsPage() {
  const filters = sessionFiltersFromHash();
  const limit = numberParam(filters.limit, 50);
  const page = numberParam(filters.page, 1);

  const sessions = useQuery({
    queryKey: ["sessions", filters],
    queryFn: () =>
      getSessions({
        order: filters.order,
        page,
        limit,
      }),
    placeholderData: keepPreviousData,
  });

  if (sessions.isLoading) return <LoadingState />;
  if (sessions.error) return <ErrorState error={sessions.error} />;

  const rows = sessions.data?.sessions ?? [];

  return (
    <section className="page-stack">
      <header className="page-header memory-page-header">
        <div>
          <p className="eyebrow">Agent streams</p>
          <h1>Sessions</h1>
        </div>
        <Badge>{sessions.data?.total_count ?? 0} total</Badge>
      </header>

      <section className="filter-panel compact-filter-panel">
        <label>
          Order
          <select
            value={filters.order}
            onChange={(event) => updateSessionFilter("order", event.target.value)}
          >
            <option value="newest_first">Recently updated</option>
            <option value="oldest_first">Oldest updated</option>
          </select>
        </label>
        <label>
          Rows
          <select
            value={filters.limit}
            onChange={(event) => updateSessionFilter("limit", event.target.value)}
          >
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </label>
      </section>

      <section className="panel table-panel">
        {rows.length === 0 ? (
          <EmptyState message="No sessions are buffered yet." />
        ) : (
          <table className="data-table sessions-table">
            <thead>
              <tr>
                <th>Session</th>
                <th>Windows</th>
                <th>Messages</th>
                <th>Produced</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((session) => (
                <tr key={session.session_id}>
                  <td>
                    <div className="scope-cell">
                      <a
                        className="memory-link mono-link"
                        href={`#/sessions/${encodeURIComponent(session.session_id)}`}
                      >
                        {session.session_id}
                      </a>
                      <span>Created {formatTime(session.created_at)}</span>
                    </div>
                  </td>
                  <td>
                    <div className="badge-stack">
                      {Object.entries(session.window_counts).length === 0 ? (
                        <Badge tone="muted">none</Badge>
                      ) : (
                        Object.entries(session.window_counts).map(([status, count]) => (
                          <Badge key={status} tone={statusTone(status)}>
                            {status}: {count}
                          </Badge>
                        ))
                      )}
                    </div>
                  </td>
                  <td>{formatNumber(session.message_count)}</td>
                  <td>{formatNumber(session.produced_unit_count)}</td>
                  <td>
                    <span className="time-cell">{formatTime(session.updated_at)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {(sessions.data?.has_more || page > 1) ? (
        <div className="pagination-bar">
          <span>
            Showing {sessions.data?.offset ?? 0}-
            {(sessions.data?.offset ?? 0) + (sessions.data?.count ?? 0)} of{" "}
            {sessions.data?.total_count ?? 0}
          </span>
          <div>
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => updateSessionFilter("page", String(page - 1))}
            >
              <span className="button-content">
                <ChevronLeft aria-hidden="true" size={16} />
                Previous
              </span>
            </button>
            <button
              type="button"
              disabled={!sessions.data?.has_more}
              onClick={() => updateSessionFilter("page", String(page + 1))}
            >
              <span className="button-content">
                Next
                <ChevronRight aria-hidden="true" size={16} />
              </span>
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

type SessionFilters = {
  order: string;
  page: string;
  limit: string;
};

function sessionFiltersFromHash(): SessionFilters {
  const query = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  return {
    order: query.get("order") ?? "newest_first",
    page: query.get("page") ?? "1",
    limit: query.get("limit") ?? "50",
  };
}

function updateSessionFilter(key: keyof SessionFilters, value: string) {
  const filters = { ...sessionFiltersFromHash(), [key]: value, page: "1" };
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
  window.location.hash = encoded ? `#/sessions?${encoded}` : "#/sessions";
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
