# Configuration

Status: draft

This document defines the intended configuration shape for NanoMem.

## 1. Goals

Configuration should be explicit, local-first, and backend-neutral. Defaults
should work for a single-user sidecar without external services.

## 2. Minimal Config

```yaml
data_dir: .nanomem

scope:
  default_namespace: personal
  allowed_namespaces:
    - personal

store:
  backend: sqlite

index:
  backend: dense

extraction:
  backend: heuristic

read:
  default_recency_policy: balanced
  default_max_units: 10
```

If `store.path` is omitted, it resolves to `${data_dir}/nanomem.db`.

## 3. Scope Config

```yaml
scope:
  default_namespace: personal
  allowed_namespaces:
    - personal
    - work
    - research
```

Rules:

- `default_namespace` must be in `allowed_namespaces`;
- capture writes to one namespace;
- read defaults to all allowed namespaces;
- extractors must not invent namespaces.

## 4. Store Config

```yaml
store:
  backend: sqlite
  path: .nanomem/nanomem.db
```

`path` may be omitted for the default local layout. `:memory:` may be used for
tests and smoke runs.

Future managed deployments may add:

```yaml
store:
  backend: postgres
  dsn_env: NANOMEM_POSTGRES_DSN
```

Secrets should be referenced through environment variables, not committed config
files.

## 5. Index Config

```yaml
index:
  backend: dense
  dense_scan_limit: 2000
  metadata_filter_keys: []
  embedding:
    backend: hashing
    dimensions: 128
```

Backend choices:

- `dense`: default bounded in-memory embedding retrieval;
- `lexical`: deterministic token fallback and debugging baseline;
- `hybrid`: lexical + dense merge;
- `lancedb`: future local persistent ANN;
- `pgvector`: future managed vector index.

LanceDB should default to `${data_dir}/lancedb` when no explicit path is set.
`metadata_filter_keys` defaults to empty. Add keys only when the host wants
those metadata fields copied into the index for filtering.

## 6. Extraction Config

```yaml
extraction:
  backend: heuristic
  confidence_threshold: 0.5
```

LLM extraction should keep provider secrets out of config:

```yaml
extraction:
  backend: llm
  model: gpt-example
  api_key_env: NANOMEM_LLM_API_KEY
  fallback_backend: heuristic
  confidence_threshold: 0.5
  strict_schema: true
  max_messages_per_chunk: 24
  max_chars_per_chunk: 12000
```

Extractor implementations may have their own chunking policy, but chunk size is
not part of `CaptureDialogue` or the public capture request.

`fallback_backend` may be `heuristic` or `null`. `strict_schema: true` means an
invalid LLM payload fails the whole model result and falls back; `false` skips
invalid units individually. `confidence_threshold` filters uncertain candidate
facts before storage.

`max_messages_per_chunk` and `max_chars_per_chunk` are extractor-internal
windowing limits. They are deliberately not part of capture requests.

## 7. Read And Render Config

```yaml
read:
  default_recency_policy: balanced
  default_max_units: 10
  default_context_budget_tokens: 1200
  renderer:
    show_namespace: false
    show_dialogue_ref: false
    show_confidence: false
    show_memory_type: false
```

Rendered text must always include time. Other labels are configurable.
`default_recency_policy` affects ranking when `time_range` is omitted; it is not
a default hard time filter.

## 8. Maintenance Config

```yaml
maintenance:
  backups:
    enabled: true
    path: .nanomem/backups/nanomem.backup.db
  exports:
    path: .nanomem/exports
  retention:
    enabled: false
    before: null
  operation_log_retention:
    enabled: true
    days: 30
```

MemoryUnit, DialogueRecord, and operation-log retention should remain separate
policy paths.

## 9. Path Resolution

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
