# Storage

Status: draft

This document defines NanoMem's durable storage boundary.

## 1. Purpose

Storage owns durable personal MemoryUnits, sessions, archived Dialogues,
DialogueWindows, operation logs, and schema state. It does not own ranking,
rendering, embedding, or ANN search.

The store is the source of truth. Indexes are derived and rebuildable.

## 2. Local Layout

Default local state lives under one data directory:

```text
.nanomem/
  nanomem.db
  lancedb/
  backups/
  exports/
```

If `store.path` is omitted, SQLite defaults to `${data_dir}/nanomem.db`.
Future local vector indexes should default under the same `data_dir`.

## 3. Durable Records

The first storage slice should persist:

- `MemoryUnit`: durable personal fact;
- `Session`: raw session grouping;
- `Dialogue`: raw control-plane dialogue evidence;
- `DialogueWindow`: append/seal/extract lifecycle control;
- operation log: capture/read/control-plane traces;
- schema migration state.

`Session`, `Dialogue`, `DialogueWindow`, and operation logs must
not be exposed through normal agent-facing read tools.

## 4. Table Responsibilities

Recommended logical tables:

```text
memory_units
sessions
dialogues
dialogue_windows
operation_logs
schema_migrations
```

`memory_units` must support filtering by:

- `owner_id`;
- `namespace`;
- `timestamp`;
- `available_at`;
- `memory_type`;
- retention/redaction state.

`dialogues` must support lookup by `dialogue_id` for audit,
re-extraction, delete, and redaction. It should not be part of retrieval and
must not carry `owner_id` or `namespace`.

`dialogue_windows` must support finding the open window for a `session_id` and
tracking status, token count, message count, seal time, extraction time, and
retry state. It must not store message content or memory scope.

## 5. SQLite Default

SQLite is the default local fact store because it is:

- dependency-light;
- easy to back up as a single file;
- good for local sidecar and single-user deployments;
- sufficient for authoritative records and metadata filters.

SQLite should not become the vector search engine. Do not store embeddings as
JSON and scan all rows for similarity in the store layer.

## 6. Store Interface

```python
class MemoryStore:
    def append_units(self, units: tuple[MemoryUnit, ...]) -> None: ...
    def get_units(self, unit_ids: tuple[str, ...]) -> tuple[MemoryUnit, ...]: ...
    def query_units(self, selector: UnitSelector) -> tuple[MemoryUnit, ...]: ...
    def put_session(self, session: Session) -> None: ...
    def put_dialogue(self, dialogue: Dialogue) -> None: ...
    def get_dialogue(self, dialogue_id: str) -> Dialogue | None: ...
    def put_dialogue_window(self, window: DialogueWindow) -> None: ...
    def query_dialogue_windows(
        self,
        selector: DialogueWindowSelector,
    ) -> tuple[DialogueWindow, ...]: ...
    def append_operation_log(self, entry: OperationLogEntry) -> None: ...
```

Implementations may split this into smaller protocols, but they should preserve
the same ownership boundary.

## 7. Retention And Redaction

MemoryUnits, Dialogues, DialogueWindows, and operation logs have separate
retention paths.

- MemoryUnit retention affects retrieval and requires index updates.
- Dialogue retention affects audit and re-extraction only.
- DialogueWindow retention affects pending/retry control only.
- Operation log retention affects observability only.

Redaction should mark or remove affected records and then rebuild or update
derived indexes. Agent-facing reads must not return redacted units. Dialogue
redaction must preserve `DialogueRef.message_range` stability by tombstoning
message slots or replacing content in place rather than renumbering messages.

## 8. Backups And Exports

Backups are physical operational copies, such as SQLite file backups.

Exports are logical user-data outputs. They should include MemoryUnits and
selected metadata. Dialogues should be exportable only through explicit
control-plane operations because they contain raw user-visible dialogue.

## 9. Migration Rules

Schema migrations must be explicit and idempotent.

Rules:

- never require index data for migration correctness;
- keep indexes rebuildable from `memory_units`;
- preserve timestamps and ids exactly;
- do not silently drop DialogueRefs;
- record migration version in the store.

Capture idempotency is deferred. It can be added later as an optional
capture-boundary store without changing MemoryUnit or read semantics.
