export type TimeRange = {
  start: string | null;
  end: string | null;
};

export type MemoryScope = {
  owner_id: string;
  namespace: string | null;
};

export type DialogueRef = {
  dialogue_id: string;
  message_range: [number, number] | null;
};

export type MemoryUnit = {
  unit_id: string;
  scope: MemoryScope;
  text: string;
  memory_type: string;
  timestamp: string;
  available_at: string;
  dialogue_refs: DialogueRef[];
  retention_until: string | null;
  redacted_at: string | null;
  metadata: Record<string, unknown>;
};

export type MemoryUnitsResponse = {
  count: number;
  total_count: number;
  offset: number;
  limit: number | null;
  has_more: boolean;
  units: MemoryUnit[];
};

export type DialogueMessage = {
  index?: number;
  role: string;
  content: string;
  timestamp: string;
  speaker_id: string | null;
  metadata: Record<string, unknown>;
  in_ref_range?: boolean;
};

export type SourceChunk = {
  status: string;
  range_label: string;
  resolved_range: [number, number] | null;
  message_count: number | null;
  resolved_message_count: number;
  raw_dialogue_available: boolean;
  messages: DialogueMessage[];
  dialogue_messages?: DialogueMessage[];
  dialogue: {
    dialogue_id: string;
    occurred_at: string;
    captured_at: string;
    checksum: string | null;
    metadata: Record<string, unknown>;
  } | null;
};

export type MemoryUnitDetailResponse = {
  unit: MemoryUnit;
  source_chunks: SourceChunk[];
};

export type StatsResponse = {
  store: string;
  path: string;
  file_size_bytes: number | null;
  schema_version: number;
  latest_schema_version: number;
  unit_count: number;
  active_unit_count: number;
  owner_count: number;
  namespace_count: number;
  dialogue_count: number;
  operation_log_count: number;
  latest_operation_at: string | null;
  oldest_timestamp: string | null;
  newest_timestamp: string | null;
  index_backend: string | null;
  index_document_count: number | null;
  index_health: "synced" | "stale" | "unknown" | string;
  index_unit_delta: number | null;
  last_reindex_at: string | null;
  metadata: {
    index?: Record<string, unknown>;
  };
};

export type ReindexResponse = {
  indexed_unit_count: number;
  index_backend: string;
  stats: Record<string, unknown>;
};

export type OperationLog = {
  log_id: string;
  operation_type: string;
  created_at: string;
  status: string;
  summary: Record<string, unknown>;
  payload: Record<string, unknown>;
};

export type OperationLogsResponse = {
  count: number;
  logs: OperationLog[];
};

export type RetrievalPreviewResponse = {
  ranked_units: Array<{
    rank: number;
    score: number;
    retrieval_text: string;
    unit: MemoryUnit;
  }>;
  context: {
    text: string;
    token_count: number;
    unit_count: number;
  };
  stats: RetrievalStats;
};

export type RetrievalStats = {
  candidate_count?: number;
  ranked_count?: number;
  returned_unit_count?: number;
  skipped_due_to_budget_count?: number;
  context_budget_tokens?: number | null;
  context_tokens?: number;
  rendered_unit_ids?: string[];
  skipped_unit_ids?: string[];
  ranked_token_estimates?: Array<{
    unit_id: string;
    render_line_tokens: number;
  }>;
  index_backend?: string;
  recency_policy?: string;
  ranking_policy?: string;
  render_policy?: string;
  [key: string]: unknown;
};
