import { Shell } from "../components/Shell";
import { IndexHealthPage } from "../features/index-health/IndexHealthPage";
import { MemoryUnitDetailPage } from "../features/memory-units/MemoryUnitDetailPage";
import { MemoryUnitsPage } from "../features/memory-units/MemoryUnitsPage";
import { OperationsPage } from "../features/operations/OperationsPage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { RetrievalPreviewPage } from "../features/retrieval-preview/RetrievalPreviewPage";
import { useHashRoute } from "./routes";

export function App() {
  const route = useHashRoute();
  return (
    <Shell>
      {route.name === "overview" && <OverviewPage />}
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
