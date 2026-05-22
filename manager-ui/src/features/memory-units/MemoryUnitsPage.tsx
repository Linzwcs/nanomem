import { useMemo, useState } from "react";
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
  const [ownerId, setOwnerId] = useState("");
  const [namespace, setNamespace] = useState("");
  const [type, setType] = useState("");
  const [text, setText] = useState("");

  const units = useQuery({
    queryKey: ["memory-units", ownerId, namespace, type],
    queryFn: () =>
      getMemoryUnits({
        owner_id: ownerId,
        namespace,
        memory_type: type,
        limit: 200,
      }),
  });

  const rows = useMemo(() => {
    const source = units.data?.units ?? [];
    const needle = text.trim().toLowerCase();
    if (!needle) return source;
    return source.filter((unit) => unit.text.toLowerCase().includes(needle));
  }, [text, units.data]);

  const columns = useMemo<ColumnDef<MemoryUnit>[]>(
    () => [
      {
        header: "Memory",
        accessorKey: "text",
        cell: ({ row }) => (
          <a href={`#/memory-units/${encodeURIComponent(row.original.unit_id)}`}>
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
        <Badge>{rows.length}</Badge>
      </header>

      <div className="filter-bar">
        <input placeholder="Owner" value={ownerId} onChange={(event) => setOwnerId(event.target.value)} />
        <input placeholder="Namespace" value={namespace} onChange={(event) => setNamespace(event.target.value)} />
        <input placeholder="Type" value={type} onChange={(event) => setType(event.target.value)} />
        <input placeholder="Text filter" value={text} onChange={(event) => setText(event.target.value)} />
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
    </section>
  );
}
