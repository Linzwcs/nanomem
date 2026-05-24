# Control Plane Boundary

Status: draft

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
human -> /manager -> /manager/api/* -> NanoMemControlService / Store / Index / ReadPipeline
```

`retrieval-preview` is the only manager feature that should call the live
`ReadPipeline`, because its job is to simulate runtime recall. Other manager
queries should read authoritative records from the store and format audit
payloads without changing runtime semantics.

## First-Version Role Model

For local development, a single local operator role is acceptable. For hosted
deployment, split permissions:

- Viewer: stats, memory list, operation logs, retrieval preview.
- Operator: reindex, backup, export, retention preview.
- Admin: redaction, delete, raw dialogue reveal, destructive retention apply.

Network exposure without authentication is out of scope.
