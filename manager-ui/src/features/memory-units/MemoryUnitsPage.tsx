import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  flexRender,
  getCoreRowModel,
  type ColumnDef,
  useReactTable,
} from "@tanstack/react-table";

import { getMemoryUnits } from "../../api/client";
import type { MemoryUnit } from "../../api/types";
import { Badge, EmptyState, ErrorState, LoadingState } from "../../components/Status";
import { TimeRangeFilter } from "../../components/TimeRangeFilter";
import { formatTime } from "../../lib/format";
import { apiTimeRange } from "../../lib/timeFilters";

export function MemoryUnitsPage() {
  const filters = memoryUnitFiltersFromHash();
  const limit = numberParam(filters.limit, 50);
  const page = numberParam(filters.page, 1);

  const units = useQuery({
    queryKey: ["memory-units", filters],
    queryFn: () => {
      const range = apiTimeRange(filters);
      return getMemoryUnits({
        owner_id: filters.owner_id,
        namespace: filters.namespace,
        memory_type: filters.memory_type,
        text: filters.text,
        start: range.start,
        end: range.end,
        order: filters.order,
        page,
        limit,
      });
    },
  });

  useEffect(() => {
    sessionStorage.setItem("nanomem.memoryUnitsHash", window.location.hash);
  });

  const rows = units.data?.units ?? [];
  const activeFilters = memoryUnitActiveFilters(filters, limit);

  const columns = useMemo<ColumnDef<MemoryUnit>[]>(
    () => [
      {
        header: "Memory",
        accessorKey: "text",
        cell: ({ row }) => (
          <div className="memory-cell">
            <a
              className="memory-link"
              href={`#/memory-units/${encodeURIComponent(row.original.unit_id)}`}
              title={row.original.text}
            >
              {row.original.text}
            </a>
            <span className="memory-id">{row.original.unit_id}</span>
          </div>
        ),
      },
      {
        header: "Scope",
        accessorKey: "scope.owner_id",
        cell: ({ row }) => (
          <div className="scope-cell">
            <strong>{row.original.scope.owner_id}</strong>
            <span>{row.original.scope.namespace ?? "default"}</span>
          </div>
        ),
      },
      {
        header: "Type",
        accessorKey: "memory_type",
        cell: ({ row }) => (
          <div className="badge-stack">
            <Badge>{row.original.memory_type}</Badge>
          </div>
        ),
      },
      {
        header: "Source",
        cell: ({ row }) => {
          const firstRef = row.original.dialogue_refs[0];
          return (
            <div className="source-cell">
              <strong>
                {row.original.dialogue_refs.length}{" "}
                {row.original.dialogue_refs.length === 1 ? "ref" : "refs"}
              </strong>
              <span>{firstRef?.dialogue_id ?? "none"}</span>
            </div>
          );
        },
      },
      {
        header: "Time",
        cell: ({ row }) => (
          <span className="time-cell">{formatTime(row.original.timestamp)}</span>
        ),
      },
    ],
    [],
  );

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (units.isLoading) return <LoadingState />;
  if (units.error) return <ErrorState error={units.error} />;

  return (
    <section className="page-stack">
      <header className="page-header memory-page-header">
        <div>
          <p className="eyebrow">Review queue</p>
          <h1>Memory Units</h1>
        </div>
        <Badge>
          {units.data?.count ?? 0} / {units.data?.total_count ?? 0}
        </Badge>
      </header>

      <section className="filter-panel memory-filter-panel">
        <label className="memory-search-field">
          Search
          <input
            placeholder="Search memory text"
            value={filters.text}
            onChange={(event) => updateMemoryUnitFilter("text", event.target.value)}
          />
        </label>
        <label>
          Owner
          <input
            placeholder="user-sim"
            value={filters.owner_id}
            onChange={(event) => updateMemoryUnitFilter("owner_id", event.target.value)}
          />
        </label>
        <label>
          Namespace
          <input
            placeholder="all"
            value={filters.namespace}
            onChange={(event) => updateMemoryUnitFilter("namespace", event.target.value)}
          />
        </label>
        <label>
          Type
          <input
            placeholder="any"
            value={filters.memory_type}
            onChange={(event) =>
              updateMemoryUnitFilter("memory_type", event.target.value)
            }
          />
        </label>
        <label>
          Order
          <select
            value={filters.order}
            onChange={(event) => updateMemoryUnitFilter("order", event.target.value)}
          >
            <option value="newest_first">Newest first</option>
            <option value="oldest_first">Oldest first</option>
          </select>
        </label>
        <label>
          Rows
          <select
            value={filters.limit}
            onChange={(event) => updateMemoryUnitFilter("limit", event.target.value)}
          >
            <option value="25">25</option>
            <option value="50">50</option>
            <option value="100">100</option>
          </select>
        </label>
        <div className="filter-time">
          <TimeRangeFilter
            compact
            value={{ start: filters.start, end: filters.end }}
            onChange={(value) =>
              updateMemoryUnitFilters({
                start: value.start,
                end: value.end,
              })
            }
          />
        </div>
        <div className="filter-actions">
          <button
            className="ghost-button"
            onClick={() => {
              window.location.hash = "#/memory-units";
            }}
            type="button"
          >
            Clear
          </button>
        </div>
      </section>

      <div className="results-strip memory-results-strip">
        <div className="filter-chip-list">
          {activeFilters.length === 0 ? (
            <span className="filter-hint">All active memory units</span>
          ) : (
            activeFilters.map((filter) => (
              <button
                aria-label={`Clear ${filter.label}`}
                className="filter-chip"
                key={filter.label}
                onClick={() => updateMemoryUnitFilters(filter.clear)}
                type="button"
              >
                {filter.label}
              </button>
            ))
          )}
        </div>
        <span className="result-count">
          Page {page} - {units.data?.total_count ?? 0} total
        </span>
      </div>

      <section className="panel table-panel">
        {rows.length === 0 ? (
          <EmptyState message="No memory units match the current filters." />
        ) : (
          <table className="data-table memory-table">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th key={header.id}>
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {(units.data?.has_more || page > 1) ? (
        <div className="pagination-bar">
          <span>
            Showing {units.data?.offset ?? 0}-
            {(units.data?.offset ?? 0) + (units.data?.count ?? 0)} of{" "}
            {units.data?.total_count ?? 0}
          </span>
          <div>
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => updateMemoryUnitFilter("page", String(page - 1))}
            >
              <span className="button-content">
                <ChevronLeft aria-hidden="true" size={16} />
                Previous
              </span>
            </button>
            <button
              type="button"
              disabled={!units.data?.has_more}
              onClick={() => updateMemoryUnitFilter("page", String(page + 1))}
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

type MemoryUnitFilters = {
  owner_id: string;
  namespace: string;
  memory_type: string;
  text: string;
  start: string;
  end: string;
  order: string;
  page: string;
  limit: string;
};

function memoryUnitFiltersFromHash(): MemoryUnitFilters {
  const query = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  return {
    owner_id: query.get("owner_id") ?? "",
    namespace: query.get("namespace") ?? "",
    memory_type: query.get("memory_type") ?? "",
    text: query.get("text") ?? "",
    start: query.get("start") ?? "",
    end: query.get("end") ?? "",
    order: query.get("order") ?? "newest_first",
    page: query.get("page") ?? "1",
    limit: query.get("limit") ?? "50",
  };
}

function updateMemoryUnitFilter(key: keyof MemoryUnitFilters, value: string) {
  updateMemoryUnitFilters({ [key]: value });
}

function updateMemoryUnitFilters(patch: Partial<MemoryUnitFilters>) {
  const filters = memoryUnitFiltersFromHash();
  const next = {
    ...filters,
    ...patch,
    page: "page" in patch ? patch.page ?? "1" : "1",
  };
  const query = new URLSearchParams();
  for (const [filterKey, filterValue] of Object.entries(next)) {
    if (
      filterValue &&
      !(filterKey === "page" && filterValue === "1") &&
      !(filterKey === "order" && filterValue === "newest_first")
    ) {
      query.set(filterKey, filterValue);
    }
  }
  const encoded = query.toString();
  window.location.hash = encoded ? `#/memory-units?${encoded}` : "#/memory-units";
}

function numberParam(value: string, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function memoryUnitActiveFilters(filters: MemoryUnitFilters, limit: number) {
  const active: Array<{ label: string; clear: Partial<MemoryUnitFilters> }> = [];
  if (filters.text) active.push({ label: `Search: ${filters.text}`, clear: { text: "" } });
  if (filters.owner_id) {
    active.push({ label: `Owner: ${filters.owner_id}`, clear: { owner_id: "" } });
  }
  if (filters.namespace) {
    active.push({ label: `Namespace: ${filters.namespace}`, clear: { namespace: "" } });
  }
  if (filters.memory_type) {
    active.push({ label: `Type: ${filters.memory_type}`, clear: { memory_type: "" } });
  }
  if (filters.order !== "newest_first") {
    active.push({ label: "Oldest first", clear: { order: "newest_first" } });
  }
  if (limit !== 50) {
    active.push({ label: `${limit} rows`, clear: { limit: "50" } });
  }
  if (filters.start || filters.end) {
    const start = filters.start || "Any start";
    const end = filters.end || "Any end";
    active.push({ label: `${start} to ${end}`, clear: { start: "", end: "" } });
  }
  return active;
}
