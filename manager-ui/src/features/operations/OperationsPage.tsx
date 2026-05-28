import { useQuery, keepPreviousData } from "@tanstack/react-query";

import { getOperationLogs } from "../../api/client";
import type { OperationLog } from "../../api/types";
import { CollapsibleFilters, ActiveFilter } from "../../components/CollapsibleFilters";
import { CopyableId } from "../../components/CopyableId";
import { Badge, EmptyState, ErrorState, LoadingState } from "../../components/Status";
import { TimeRangeFilter } from "../../components/TimeRangeFilter";
import { formatTimeShort } from "../../lib/format";
import { apiTimeRange } from "../../lib/timeFilters";

export function OperationsPage() {
  const filters = operationFiltersFromHash();
  const limit = numberParam(filters.limit, 100);
  const logs = useQuery({
    queryKey: ["operation-logs", filters],
    queryFn: () => {
      const range = apiTimeRange(filters);
      return getOperationLogs({
        owner_id: filters.owner_id,
        namespace: filters.namespace,
        operation_type: filters.operation_type,
        status: filters.status,
        start: range.start,
        end: range.end,
        limit,
      });
    },
    placeholderData: keepPreviousData,
  });

  if (logs.isLoading) return <LoadingState />;
  if (logs.error) return <ErrorState error={logs.error} />;

  const rows = logs.data?.logs ?? [];
  const activeFilters = operationActiveFilters(filters, limit);

  return (
    <section className="page-stack">
      <header className="page-header memory-page-header">
        <div>
          <p className="eyebrow">Audit trail</p>
          <h1>Operations</h1>
        </div>
        <Badge>{logs.data?.count ?? rows.length}</Badge>
      </header>

      <CollapsibleFilters
        active={activeFilters}
        emptyHint="All operation logs"
        onClearAll={() => {
          window.location.hash = "#/operations";
        }}
      >
        <section className="filter-panel operations-filter">
          <label>
            Operation
            <input
              placeholder="capture, read, reindex"
              value={filters.operation_type}
              onChange={(event) =>
                updateOperationFilters({ operation_type: event.target.value })
              }
            />
          </label>
          <label>
            Status
            <select
              value={filters.status}
              onChange={(event) => updateOperationFilters({ status: event.target.value })}
            >
              <option value="">any</option>
              <option value="ok">ok</option>
              <option value="error">error</option>
            </select>
          </label>
          <label>
            Owner
            <input
              placeholder="optional"
              value={filters.owner_id}
              onChange={(event) => updateOperationFilters({ owner_id: event.target.value })}
            />
          </label>
          <label>
            Namespace
            <input
              placeholder="optional"
              value={filters.namespace}
              onChange={(event) => updateOperationFilters({ namespace: event.target.value })}
            />
          </label>
          <label>
            Rows
            <select
              value={filters.limit}
              onChange={(event) => updateOperationFilters({ limit: event.target.value })}
            >
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="200">200</option>
            </select>
          </label>
          <div className="filter-time">
            <TimeRangeFilter
              compact
              value={{ start: filters.start, end: filters.end }}
              onChange={(value) =>
                updateOperationFilters({ start: value.start, end: value.end })
              }
            />
          </div>
        </section>
      </CollapsibleFilters>

      <div className="results-strip operations-results-strip">
        <span className="result-count">
          Showing {rows.length} of {limit}
        </span>
      </div>

      <section className="panel table-panel">
        {rows.length === 0 ? (
          <EmptyState message="No operation logs are available." />
        ) : (
          <table className="data-table operations-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Operation</th>
                <th>Status</th>
                <th>Scope</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((log) => {
                const namespace = operationNamespace(log);
                return (
                  <tr key={log.log_id}>
                    <td>
                      <span className="time-cell time-cell-short">
                        {formatTimeShort(log.created_at)}
                      </span>
                    </td>
                    <td>
                      <div className="operation-cell-inline">
                        <strong>{log.operation_type}</strong>
                        <CopyableId value={log.log_id} variant="compact" />
                      </div>
                    </td>
                    <td className="status-dot-cell">
                      <span
                        aria-label={log.status}
                        className={`status-dot status-dot-${log.status}`}
                        title={log.status}
                      />
                    </td>
                    <td>
                      <span className="scope-inline">
                        <strong>{operationOwner(log)}</strong>
                        {namespace && namespace !== "default" ? (
                          <span className="scope-inline-ns">{namespace}</span>
                        ) : null}
                      </span>
                    </td>
                    <td>
                      <div className="summary-cell">
                        {summaryItems(log, 3).map((item) => (
                          <span className="summary-token" key={item.key}>
                            <strong>{item.key}</strong>
                            {item.value}
                          </span>
                        ))}
                        {summaryOverflow(log, 3) > 0 ? (
                          <span className="summary-overflow">
                            +{summaryOverflow(log, 3)}
                          </span>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </section>
  );
}

type OperationFilters = {
  owner_id: string;
  namespace: string;
  operation_type: string;
  status: string;
  start: string;
  end: string;
  limit: string;
};

function operationFiltersFromHash(): OperationFilters {
  const query = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  return {
    owner_id: query.get("owner_id") ?? "",
    namespace: query.get("namespace") ?? "",
    operation_type: query.get("operation_type") ?? "",
    status: query.get("status") ?? "",
    start: query.get("start") ?? "",
    end: query.get("end") ?? "",
    limit: query.get("limit") ?? "100",
  };
}

function updateOperationFilters(patch: Partial<OperationFilters>) {
  const next = { ...operationFiltersFromHash(), ...patch };
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(next)) {
    if (value) query.set(key, value);
  }
  const encoded = query.toString();
  window.location.hash = encoded ? `#/operations?${encoded}` : "#/operations";
}

function numberParam(value: string, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function operationActiveFilters(filters: OperationFilters, limit: number): ActiveFilter[] {
  const active: ActiveFilter[] = [];
  if (filters.operation_type) {
    active.push({
      label: `Operation: ${filters.operation_type}`,
      onClear: () => updateOperationFilters({ operation_type: "" }),
    });
  }
  if (filters.status) {
    active.push({
      label: `Status: ${filters.status}`,
      onClear: () => updateOperationFilters({ status: "" }),
    });
  }
  if (filters.owner_id) {
    active.push({
      label: `Owner: ${filters.owner_id}`,
      onClear: () => updateOperationFilters({ owner_id: "" }),
    });
  }
  if (filters.namespace) {
    active.push({
      label: `Namespace: ${filters.namespace}`,
      onClear: () => updateOperationFilters({ namespace: "" }),
    });
  }
  if (limit !== 100) {
    active.push({
      label: `${limit} rows`,
      onClear: () => updateOperationFilters({ limit: "100" }),
    });
  }
  if (filters.start || filters.end) {
    active.push({
      label: `${filters.start || "Any start"} to ${filters.end || "Any end"}`,
      onClear: () => updateOperationFilters({ start: "", end: "" }),
    });
  }
  return active;
}

function operationOwner(log: OperationLog) {
  return (
    log.scope?.owner_id ??
    stringValue(log.summary.owner_id) ??
    stringValue(log.payload.owner_id) ??
    "global"
  );
}

function operationNamespace(log: OperationLog) {
  return (
    log.scope?.namespace ??
    stringValue(log.summary.namespace) ??
    namespacesValue(log.payload.namespaces) ??
    "default"
  );
}

function summaryItems(log: OperationLog, limit = 5) {
  const entries = Object.entries(log.summary).slice(0, limit);
  if (entries.length === 0) return [{ key: "summary", value: "empty" }];
  return entries.map(([key, value]) => ({
    key,
    value: compactValue(value),
  }));
}

function summaryOverflow(log: OperationLog, limit: number) {
  const total = Object.keys(log.summary).length;
  return Math.max(0, total - limit);
}

function compactValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "none";
  if (Array.isArray(value)) return `${value.length} items`;
  if (typeof value === "object") return "object";
  return String(value);
}

function stringValue(value: unknown) {
  return typeof value === "string" && value ? value : null;
}

function namespacesValue(value: unknown) {
  if (Array.isArray(value) && value.every((item) => typeof item === "string")) {
    return value.length > 0 ? value.join(", ") : "all namespaces";
  }
  return null;
}

function shortId(value: string) {
  return value.length > 18 ? `${value.slice(0, 18)}...` : value;
}
