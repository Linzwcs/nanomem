import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  type ColumnDef,
  useReactTable,
} from "@tanstack/react-table";

import { getMemoryUnits } from "../../api/client";
import type { MemoryUnit } from "../../api/types";
import { Badge, EmptyState, ErrorState, LoadingState } from "../../components/Status";
import { formatTime } from "../../lib/format";

export function MemoryUnitsPage() {
  const filters = memoryUnitFiltersFromHash();
  const limit = numberParam(filters.limit, 50);
  const page = numberParam(filters.page, 1);

  const units = useQuery({
    queryKey: ["memory-units", filters],
    queryFn: () =>
      getMemoryUnits({
        owner_id: filters.owner_id,
        namespace: filters.namespace,
        memory_type: filters.memory_type,
        text: filters.text,
        start: filters.start,
        end: filters.end,
        page,
        limit,
      }),
  });

  useEffect(() => {
    sessionStorage.setItem("nanomem.memoryUnitsHash", window.location.hash);
  });

  const rows = units.data?.units ?? [];

  const columns = useMemo<ColumnDef<MemoryUnit>[]>(
    () => [
      {
        header: "Memory",
        accessorKey: "text",
        cell: ({ row }) => (
          <a
            href={`#/memory-units/${encodeURIComponent(row.original.unit_id)}`}
          >
            {row.original.text}
          </a>
        ),
      },
      {
        header: "Type",
        accessorKey: "memory_type",
        cell: ({ getValue }) => <Badge>{String(getValue())}</Badge>,
      },
      {
        header: "Namespace",
        cell: ({ row }) => <Badge tone="muted">{row.original.scope.namespace}</Badge>,
      },
      {
        header: "Confidence",
        cell: ({ row }) => row.original.confidence?.toFixed(2) ?? "none",
      },
      {
        header: "Time",
        cell: ({ row }) => formatTime(row.original.timestamp),
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
      <header className="page-header">
        <div>
          <p className="eyebrow">Review queue</p>
          <h1>Memory Units</h1>
        </div>
        <Badge>
          {units.data?.count ?? 0} / {units.data?.total_count ?? 0}
        </Badge>
      </header>

      <div className="filter-bar">
        <input
          placeholder="Owner"
          value={filters.owner_id}
          onChange={(event) => updateMemoryUnitFilter("owner_id", event.target.value)}
        />
        <input
          placeholder="Namespace"
          value={filters.namespace}
          onChange={(event) => updateMemoryUnitFilter("namespace", event.target.value)}
        />
        <input
          placeholder="Type"
          value={filters.memory_type}
          onChange={(event) =>
            updateMemoryUnitFilter("memory_type", event.target.value)
          }
        />
        <input
          placeholder="Text filter"
          value={filters.text}
          onChange={(event) => updateMemoryUnitFilter("text", event.target.value)}
        />
        <input
          placeholder="Start time"
          value={filters.start}
          onChange={(event) => updateMemoryUnitFilter("start", event.target.value)}
        />
        <input
          placeholder="End time"
          value={filters.end}
          onChange={(event) => updateMemoryUnitFilter("end", event.target.value)}
        />
      </div>

      <section className="panel table-panel">
        {rows.length === 0 ? (
          <EmptyState message="No memory units match the current filters." />
        ) : (
          <table className="data-table">
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
            Previous
          </button>
          <button
            type="button"
            disabled={!units.data?.has_more}
            onClick={() => updateMemoryUnitFilter("page", String(page + 1))}
          >
            Next
          </button>
        </div>
      </div>
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
    page: query.get("page") ?? "1",
    limit: query.get("limit") ?? "50",
  };
}

function updateMemoryUnitFilter(key: keyof MemoryUnitFilters, value: string) {
  const filters = memoryUnitFiltersFromHash();
  const query = new URLSearchParams();
  for (const [filterKey, filterValue] of Object.entries({
    ...filters,
    [key]: value,
    page: key === "page" ? value : "1",
  })) {
    if (filterValue && !(filterKey === "page" && filterValue === "1")) {
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
