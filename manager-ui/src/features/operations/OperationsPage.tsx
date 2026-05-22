import { useQuery } from "@tanstack/react-query";

import { getOperationLogs } from "../../api/client";
import { Badge, EmptyState, ErrorState, LoadingState } from "../../components/Status";
import { formatTime, jsonPreview } from "../../lib/format";

export function OperationsPage() {
  const logs = useQuery({
    queryKey: ["operation-logs"],
    queryFn: () => getOperationLogs({ limit: 100 }),
  });

  if (logs.isLoading) return <LoadingState />;
  if (logs.error) return <ErrorState error={logs.error} />;

  const rows = logs.data?.logs ?? [];

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Audit trail</p>
          <h1>Operations</h1>
        </div>
        <Badge>{rows.length}</Badge>
      </header>

      <section className="panel table-panel">
        {rows.length === 0 ? (
          <EmptyState message="No operation logs are available." />
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Type</th>
                <th>Status</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((log) => (
                <tr key={log.log_id}>
                  <td>{formatTime(log.created_at)}</td>
                  <td>{log.operation_type}</td>
                  <td>
                    <Badge tone={log.status === "ok" ? "good" : "warn"}>
                      {log.status}
                    </Badge>
                  </td>
                  <td>
                    <pre className="inline-json">{jsonPreview(log.summary)}</pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </section>
  );
}
