# Configuration

Status: developer preview candidate

This document defines the current configuration shape implemented by NanoMem.
It intentionally describes the working local sidecar path first, then optional
provider and index extensions.

## 1. Developer Preview Defaults

```yaml
data_dir: .nanomem

store:
  backend: sqlite

index:
  backend: dense

extraction:
  backend: heuristic
  max_dialogue_tokens: 512

read:
  default_recency_policy: balanced
  default_max_units: 10
```

With this config, NanoMem uses SQLite as the authoritative fact store,
deterministic local hashing embeddings, an in-memory dense index, and the
heuristic extractor. It requires no network providers.

Default local state resolves under `data_dir`:

```text
.nanomem/
  nanomem.db      # authoritative SQLite store
  lancedb/        # optional persistent local vector index
  backups/        # recommended backup output directory
  exports/        # recommended export output directory
```

If `store.path` is omitted, it resolves to `${data_dir}/nanomem.db`. If
`index.path` is omitted, it resolves to `${data_dir}/lancedb`.

## 2. Store Config

```yaml
store:
  backend: sqlite
  path: .nanomem/nanomem.db
```

`path` may be omitted for the default local layout. `:memory:` may be used for
tests and smoke runs.

Developer preview supports only `store.backend: sqlite`. Future managed
deployments may add Postgres, but it is not a current local target.

Secrets should be referenced through environment variables, not committed config
files.

## 3. Dense Local Index

```yaml
index:
  backend: dense
  rebuild_on_startup: true
  dense_scan_limit: 2000
  metadata_filter_keys: []
  embedding:
    backend: hashing
    dimensions: 128
```

`dense` is the default. It is a bounded in-memory vector index over stored
MemoryUnits. It is good for local development, tests, and small personal stores.
It is not an ANN backend.

`rebuild_on_startup` defaults to `true`. With the current in-memory dense index
backends, NanoMem treats SQLite as the authoritative fact store and rebuilds the
active index from stored `MemoryUnit` records whenever a configured service
starts. Set it to `false` only for specialized tests or hosts that rebuild the
index explicitly.

`dense_scan_limit` caps per-query in-memory similarity work. For larger local
stores, prefer the optional LanceDB backend instead of raising this indefinitely.

## 4. Optional LanceDB Index

Use LanceDB when a local sidecar needs a persistent vector index without running
another server.

```yaml
data_dir: .nanomem

store:
  backend: sqlite

index:
  backend: lancedb
  path: .nanomem/lancedb
  table: memory_units
  distance_type: cosine
  embedding:
    backend: hashing
    dimensions: 128
```

Install with:

```bash
python -m pip install -e ".[dev,lancedb]"
```

SQLite remains the source of truth. LanceDB stores retrieval fields and vectors
only and must be rebuildable from SQLite.

Validate the local LanceDB path with:

```bash
bash scripts/smoke_lancedb_index.sh
python -m pytest tests/index/test_lancedb_integration.py
```

Other implemented index backends:

- `lexical`: deterministic token-overlap baseline;
- `hybrid`: merges lexical and dense scores;
- `dense`: default local in-memory vector baseline.

## 5. Extraction Config

```yaml
extraction:
  backend: heuristic
  max_dialogue_tokens: 512
```

LLM extraction should keep provider secrets out of config:

```yaml
extraction:
  backend: llm
  model: gpt-example
  api_key_env: NANOMEM_LLM_API_KEY
  fallback_backend: heuristic
  strict_schema: true
  max_messages_per_chunk: 24
  max_chars_per_chunk: 12000
```

Extractor implementations may have their own chunking policy, but chunk size is
not part of `CaptureDialogue` or the public capture request.

`max_dialogue_tokens` controls capture buffering for requests with
`session_id`. When the open dialogue window reaches this estimate, NanoMem
seals it and runs extraction. Requests without `session_id` are treated as
complete dialogues and extract immediately.

`fallback_backend` may be `heuristic` or `null`. `strict_schema: true` means an
invalid LLM payload fails the whole model result and falls back; `false` skips
invalid units individually.

`max_messages_per_chunk` and `max_chars_per_chunk` are extractor-internal
windowing limits. They are deliberately not part of capture requests.

## 6. Read Config

```yaml
read:
  default_recency_policy: balanced
  default_max_units: 10
```

`default_recency_policy` affects ranking when a read request omits
`recency_policy`. It is not a hard time filter. Read requests may still provide
`time_range` for candidate filtering, `max_units`, and
`context_budget_tokens`.

Rendered text always includes time. Render formatting is not configurable in the
current developer preview.

## 7. Maintenance Config

```yaml
maintenance:
  integrity_check: true
  backup:
    enabled: true
    path: .nanomem/backups/nanomem.backup.db
    overwrite: false
  export:
    enabled: true
    path: .nanomem/exports/export.json
    include_operation_logs: true
    overwrite: false
  retention:
    enabled: false
    before: null
    max_age_days: null
  operation_log_retention:
    enabled: false
    before: null
    max_age_days: null
```

MemoryUnit, Dialogue, and operation-log retention should remain separate
policy paths.

## 8. Path Resolution

Relative paths resolve from the process working directory unless a host adapter
provides an explicit config root.

Recommended local layout:

```text
.nanomem/
  nanomem.db
  lancedb/
  backups/
  exports/
```

All generated local state should stay under `data_dir` by default.

## 9. Sidecar Installation Guidance

For developer preview, prefer project-local or user-local configuration:

```text
project/.nanomem/nanomem.db
project/nanomem.json
```

or:

```text
~/.config/nanomem/nanomem.json
~/.local/share/nanomem/nanomem.db
```

Do not require system-wide installation for ordinary agent integration. Agent
hooks should connect to a local HTTP sidecar through `NANOMEM_BASE_URL`,
`NANOMEM_OWNER_ID`, and optional `NANOMEM_NAMESPACE`.
