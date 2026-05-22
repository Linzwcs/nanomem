import type {
  MemoryUnitDetailResponse,
  MemoryUnitsResponse,
  OperationLogsResponse,
  RetrievalPreviewResponse,
  StatsResponse,
} from "./types";

type QueryValue = string | number | boolean | null | undefined;

export async function getStats() {
  return apiGet<StatsResponse>("/manager/api/stats");
}

export async function getMemoryUnits(params: Record<string, QueryValue>) {
  return apiGet<MemoryUnitsResponse>(
    `/manager/api/memory-units${queryString(params)}`,
  );
}

export async function getMemoryUnit(unitId: string) {
  return apiGet<MemoryUnitDetailResponse>(
    `/manager/api/memory-units/${encodeURIComponent(unitId)}`,
  );
}

export async function getOperationLogs(params: Record<string, QueryValue>) {
  return apiGet<OperationLogsResponse>(
    `/manager/api/operation-logs${queryString(params)}`,
  );
}

export async function previewRetrieval(payload: Record<string, unknown>) {
  return apiPost<RetrievalPreviewResponse>(
    "/manager/api/retrieval-preview",
    payload,
  );
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
  });
  return decode<T>(response);
}

async function apiPost<T>(path: string, payload: Record<string, unknown>): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return decode<T>(response);
}

async function decode<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok) {
    const error = payload?.error || response.statusText;
    throw new Error(String(error));
  }
  return payload as T;
}

function queryString(params: Record<string, QueryValue>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  }
  const encoded = query.toString();
  return encoded ? `?${encoded}` : "";
}
