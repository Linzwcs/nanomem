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

export type SessionSummary = {
  session_id: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  dialogue_count: number;
  window_count: number;
  window_counts: Record<string, number>;
  message_count: number;
  produced_unit_count: number;
  latest_message_at: string | null;
};

export type DialogueSummary = {
  dialogue_id: string;
  session_id: string | null;
  started_at: string;
  ended_at: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  checksum: string | null;
  metadata: Record<string, unknown>;
  retention_until: string | null;
  redacted_at: string | null;
};

export type DialogueWindow = {
  session_id: string;
  dialogue_id: string;
  status: string;
  token_count: number;
  message_count: number;
  created_at: string;
  updated_at: string;
  sealed_at: string | null;
  extracted_at: string | null;
  seal_reason: string | null;
  metadata: Record<string, unknown>;
  dialogue: DialogueSummary | null;
  produced_unit_count: number;
  produced_unit_ids: string[];
};

export type SessionStreamMessage = DialogueMessage & {
  index: number;
  dialogue_id: string;
  local_index: number;
  window_status: string | null;
  window_seal_reason: string | null;
  produced_unit_ids: string[];
};

export type SessionsResponse = {
  count: number;
  total_count: number;
  offset: number;
  limit: number | null;
  has_more: boolean;
  sessions: SessionSummary[];
};

export type SessionDetailResponse = {
  session: SessionSummary;
  dialogues: DialogueSummary[];
  windows: DialogueWindow[];
  messages: SessionStreamMessage[];
  produced_units: MemoryUnit[];
  operation_logs: OperationLog[];
};

export type DialogueWindowsResponse = {
  count: number;
  total_count: number;
  offset: number;
  limit: number | null;
  has_more: boolean;
  windows: DialogueWindow[];
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
  ref: DialogueRef;
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
    session_id: string | null;
    started_at: string;
    ended_at: string;
    created_at: string;
    updated_at: string;
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
  session_count: number;
  dialogue_count: number;
  dialogue_window_count: number;
  open_dialogue_window_count: number;
  operation_log_count: number;
  applied_schema_migration_count?: number;
  pending_schema_migration_count?: number;
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
  top_owners?: Array<{
    owner_id: string;
    namespace: string | null;
    unit_count: number;
  }>;
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
  scope: MemoryScope | null;
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
