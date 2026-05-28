# Control Plane Boundary

Status: active

## Purpose

NanoMem Manager is a control plane for NanoMem memory stores. It helps a
human answer:

- What durable memories exist for an owner and namespace?
- Which dialogue evidence produced each `MemoryUnit`?
- Did extraction skip anything, and why?
- Is the active index fresh relative to the authoritative store?
- Which retention, export, or redaction operation would affect which records?

The console should feel like a focused operations and audit tool, not a chat
client or a general document browser.

## Non-Goals

The manager must not become:

- an agent runtime interface;
- a replacement for `/v1/capture` or `/v1/read`;
- a chat replay product;
- a file manager for arbitrary local documents or multimodal assets;
- an MCP tool exposed to normal agents;
- a second implementation of retrieval, ranking, or rendering.

## Core Principle

```text
MemoryUnit is the durable fact.
Dialogue is audit evidence.
Index is a derived retrieval cache.
OperationLogEntry is the operational trail.
```

This boundary matters because NanoMem stores fine-grained personal memory, not
all user data. Source dialogue is available for audit, correction, and privacy
operations, but it is not part of the normal retrieval corpus.

## Runtime Separation

The runtime path remains:

```text
agent -> /v1/capture -> store + index
agent -> /v1/read    -> read pipeline -> rendered memory context
```

The manager path is:

```text
human -> /manager -> /manager/api/* -> ControlFacade
                                    -> NanoMemAdminService / NanoMemService.read()
```

`retrieval-preview` is the only manager feature that calls the live read
pipeline, because its job is to simulate runtime recall. Other manager
queries read authoritative records from the store and format audit
payloads without changing runtime semantics.

## First-Version Role Model

For local development, a single local operator role is acceptable. The HTTP
control plane only exposes inspection + retrieval preview + reindex; the
heavier maintenance / privacy workflows (backup, export, retention,
redaction, integrity) are CLI-only today and inherit local filesystem
permissions. See `05-operations-and-privacy.md`.

For a future hosted deployment, role separation will be required:

- Viewer: stats, sessions, memory list, operation logs, retrieval preview.
- Operator: + reindex through HTTP; backup / export / retention through
  the operator's shell.
- Admin: + redaction / delete / raw dialogue reveal (all currently behind
  shell access).

Network exposure without authentication is out of scope.

