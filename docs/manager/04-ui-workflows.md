# UI Workflows

Status: draft

The manager UI should make memory state explainable without turning dialogue into
the main product surface.

## Memory Review

Default to the `Memory Units` list. Operators should be able to scan recent
facts, filter by owner, namespace, type, time range, and redaction, then open a
full-page detail route.

Time filtering should be prominent but precise. The list should provide quick
presets such as all time, recent days, and current month, plus explicit start
and end dates. The visible dates are local calendar dates; requests must send
concrete ISO boundaries so a selected end date includes the whole day.

The list should also expose ordering next to the time controls. `newest_first`
is the default review mode; `oldest_first` is useful when auditing historical
imports or retention boundaries.

The detail page should use this structure:

```text
Fact
Evidence
Quality
Lifecycle
Raw JSON
```

`Fact` is the durable memory. `Evidence` shows source dialogue snippets and
metadata. `Quality` explains missing refs, redaction, and review reasons.
`Lifecycle` shows timestamps, retention, and produced-from dialogue times.

## Evidence Display

Source dialogue should be evidence, not a chat replay.

Default display:

- source status badge;
- dialogue id and checksum;
- occurred/captured timestamps;
- exact message range;
- extracted messages in a compact transcript.

For hosted deployments, raw message content should require explicit reveal and
write an audit log. Missing, redacted, empty, and clamped evidence ranges should
have separate states so operators can distinguish data loss from policy hiding.

## Retrieval Lab

Retrieval Lab is a runtime recall simulator, not general search. It should show:

- request payload;
- ranked units;
- score breakdown;
- rendered context;
- candidate/ranked/returned counts;
- skipped-due-to-budget count;
- per-ranked-unit rendered/skipped state and render-line token estimate;
- index backend.

From each ranked result, link back to MemoryUnit detail and source evidence.

Retrieval Lab has two separate time controls:

- `query_time`: the simulated current time for recency ranking;
- `memory time range`: a hard filter over MemoryUnit evidence timestamps.

These controls should remain visually separate because changing `query_time`
changes ranking, while changing the memory range changes which facts are
eligible for retrieval at all.

## Operation Logs

Operation logs should support filters for operation type, status, owner/scope,
and time range. The operation-log time range applies to log creation time, not
the underlying memory evidence time. A log detail view should show summary first
and raw payload only when useful.

## Empty And Error States

Every page should have explicit states for:

- no matching records;
- missing dialogue reference;
- redacted dialogue;
- stale or empty index;
- permission denied;
- failed control operation.

These states are part of the product because operators need to distinguish
normal absence from data integrity problems.
