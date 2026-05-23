# Control API

Status: draft

`/manager/api/*` is a control-plane API. It should observe, diagnose, and maintain
the memory store without redefining capture/read behavior.

## Architecture

```text
/manager/api/*
  -> thin HTTP routing and serialization
  -> NanoMemControlService for control-plane use cases
  -> Store / Index / NanoMemService.read()
```

HTTP handlers should only parse inputs, call services, and serialize results.
They should not duplicate store, ranking, rendering, or redaction logic.

## Observation Endpoints

```text
GET /manager/api/stats
GET /manager/api/schema
GET /manager/api/integrity
GET /manager/api/index-health
GET /manager/api/operation-logs
```

Observation endpoints are read-only. They should support selectors and
pagination for large stores.

`stats` includes index health fields for the active backend:

- `active_unit_count`: non-redacted MemoryUnits in the authoritative store;
- `index_document_count`: documents visible to the active index when supported;
- `index_health`: `synced`, `stale`, or `unknown`;
- `index_unit_delta`: `active_unit_count - index_document_count`;
- `last_reindex_at`: latest successful manager reindex operation timestamp.

## Memory And Evidence Endpoints

```text
GET /manager/api/memory-units
GET /manager/api/memory-units/{unit_id}
GET /manager/api/memory-units/{unit_id}/source
GET /manager/api/dialogues/{dialogue_id}
GET /manager/api/dialogues/{dialogue_id}/produced-units
```

Memory list endpoints return canonical `MemoryUnit` fields. Detail endpoints may
add derived audit fields such as `source_chunks`, but those fields must not
change the stored memory model.

Each source chunk should include:

- `status`: `ok`, `missing_dialogue`, `redacted_dialogue`,
  `empty_range`, or `out_of_range_clamped`;
- `range_label` and `resolved_range`;
- `message_count` and `resolved_message_count`;
- `raw_dialogue_available`;
- `requires_explicit_reveal`.

## Diagnosis Endpoints

```text
POST /manager/api/retrieval-preview
POST /manager/api/reindex
```

`retrieval-preview` must call `NanoMemService.read()` so the result matches
agent runtime behavior. It should mark logs as manager previews or allow preview
logging to be disabled.

`reindex` rebuilds derived index state from the authoritative store. If partial
reindex is introduced, the response must clearly say whether the active index
was fully rebuilt or incrementally updated.

Manager-triggered reindex operations write an operation log entry with operation
type `reindex`, affected count, backend name, and selector metadata.

## Maintenance Endpoints

```text
POST /manager/api/backup
POST /manager/api/export
POST /manager/api/retention/preview
POST /manager/api/retention/apply
POST /manager/api/redactions/preview
POST /manager/api/redactions/apply
```

Every destructive or privacy-sensitive operation needs:

- dry-run preview;
- explicit confirmation on apply;
- scoped selector;
- affected counts and samples;
- operation log entry;
- clear statement about whether reindex is required afterward.
