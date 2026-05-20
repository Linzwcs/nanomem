# Admin API

Status: draft

`/admin/api/*` is a control-plane API. It should observe, diagnose, and maintain
the memory store without redefining capture/read behavior.

## Architecture

```text
/admin/api/*
  -> thin HTTP routing and serialization
  -> NanoMemAdminService for admin use cases
  -> Store / Index / NanoMemService.read()
```

HTTP handlers should only parse inputs, call services, and serialize results.
They should not duplicate store, ranking, rendering, or redaction logic.

## Observation Endpoints

```text
GET /admin/api/stats
GET /admin/api/schema
GET /admin/api/integrity
GET /admin/api/index-health
GET /admin/api/operation-logs
```

Observation endpoints are read-only. They should support selectors and
pagination for large stores.

## Memory And Evidence Endpoints

```text
GET /admin/api/memory-units
GET /admin/api/memory-units/{unit_id}
GET /admin/api/memory-units/{unit_id}/source
GET /admin/api/dialogues/{dialogue_id}
GET /admin/api/dialogues/{dialogue_id}/produced-units
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
POST /admin/api/retrieval-preview
POST /admin/api/reindex
```

`retrieval-preview` must call `NanoMemService.read()` so the result matches
agent runtime behavior. It should mark logs as admin previews or allow preview
logging to be disabled.

`reindex` rebuilds derived index state from the authoritative store. If partial
reindex is introduced, the response must clearly say whether the active index
was fully rebuilt or incrementally updated.

## Maintenance Endpoints

```text
POST /admin/api/backup
POST /admin/api/export
POST /admin/api/retention/preview
POST /admin/api/retention/apply
POST /admin/api/redactions/preview
POST /admin/api/redactions/apply
```

Every destructive or privacy-sensitive operation needs:

- dry-run preview;
- explicit confirmation on apply;
- scoped selector;
- affected counts and samples;
- operation log entry;
- clear statement about whether reindex is required afterward.
