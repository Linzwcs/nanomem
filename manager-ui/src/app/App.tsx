import { Shell } from "../components/Shell";
import { IndexHealthPage } from "../features/index-health/IndexHealthPage";
import { MemoryUnitDetailPage } from "../features/memory-units/MemoryUnitDetailPage";
import { MemoryUnitsPage } from "../features/memory-units/MemoryUnitsPage";
import { OperationsPage } from "../features/operations/OperationsPage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { RetrievalPreviewPage } from "../features/retrieval-preview/RetrievalPreviewPage";
import { DialogueWindowsPage } from "../features/dialogue-windows/DialogueWindowsPage";
import { SessionDetailPage } from "../features/sessions/SessionDetailPage";
import { SessionsPage } from "../features/sessions/SessionsPage";
import { useHashRoute } from "./routes";

export function App() {
  const route = useHashRoute();
  return (
    <Shell>
      {route.name === "overview" && <OverviewPage />}
      {route.name === "sessions" && <SessionsPage />}
      {route.name === "session-detail" && (
        <SessionDetailPage sessionId={route.sessionId} />
      )}
      {route.name === "dialogue-windows" && <DialogueWindowsPage />}
      {route.name === "memory-units" && <MemoryUnitsPage />}
      {route.name === "memory-unit-detail" && (
        <MemoryUnitDetailPage unitId={route.unitId} />
      )}
      {route.name === "retrieval-preview" && <RetrievalPreviewPage />}
      {route.name === "operations" && <OperationsPage />}
      {route.name === "index-health" && <IndexHealthPage />}
    </Shell>
  );
}
