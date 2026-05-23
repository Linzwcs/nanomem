# UI Workflows

Status: draft

The manager UI should make memory state explainable without turning dialogue into
the main product surface.

## Memory Review

Default to the `Memory Units` list. Operators should be able to scan recent
facts, filter by owner, namespace, type, time range, confidence, and redaction,
then open a full-page detail route.

The detail page should use this structure:

```text
Fact
Evidence
Quality
Lifecycle
Raw JSON
```

`Fact` is the durable memory. `Evidence` shows source dialogue snippets and
metadata. `Quality` explains confidence, missing refs, redaction, and review
reasons. `Lifecycle` shows timestamps, retention, and produced-from dialogue
times.

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

## Operation Logs

Operation logs should support filters for operation type, status, owner/scope,
and time range. A log detail view should show summary first and raw payload only
when useful.

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
