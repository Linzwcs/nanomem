# Product Boundary

Status: draft

This document defines what NanoMem owns. It should be read before API,
storage, indexing, or integration design.

## 1. Product Thesis

NanoMem exists because long-term personal memory has different semantics from
workspace context.

Workspace context is already stored in files, repositories, logs, artifacts,
skills, object stores, and business systems. Modern agents can read those
sources directly. NanoMem should not duplicate them.

NanoMem owns durable, user-related personal facts that should survive across
sessions and projects.

## 2. In Scope

NanoMem should store fine-grained personal MemoryUnits in these categories:

- `preference`: user preferences for style, tools, workflows, or interaction;
- `correction`: user corrections to agent behavior;
- `habit`: repeated cross-project user behavior or working style;
- `background`: durable user background that affects interaction;
- `relationship`: durable relationship facts about people, tools, agents, or
  organizations;
- `user_event`: events that happened to the user or decisions the user made
  and that may affect future interaction;
- `agent_interaction_event`: user-visible agent actions that changed future
  collaboration expectations.

Examples:

```text
The user said they prefer concise Chinese answers.
The user corrected the agent not to auto-commit code.
The user usually wants design boundaries discussed before implementation.
The user decided NanoMem should not become an all-in-one workspace memory.
The agent auto-committed code and the user reacted negatively.
```

## 3. Out Of Scope

NanoMem should not store:

- project docs, README files, ADRs, source code, or config files;
- repository-specific rules such as test commands or build steps;
- skills, including `SKILL.md`, scripts, templates, references, and assets;
- raw tool calls, tool results, stdout, CI logs, or build artifacts;
- current task plans, scratchpads, issue status, or PR progress;
- raw PDFs, images, audio, video, screenshots, datasets, or binary assets;
- complete chat archives;
- hidden reasoning, chain-of-thought, or intermediate agent planning;
- external business records that can be reread from their system of record.

Those resources should remain outside NanoMem as source-of-truth artifacts. If
they matter for personal memory, the agent should consume them and expose the
relevant information in user-visible dialogue; NanoMem then captures from that
dialogue.

## 4. Boundary With Agent Harnesses

Coding and local agent harnesses should use NanoMem as a sidecar:

```text
workspace/tools = current task and artifact context
NanoMem         = long-term personal evidence
```

Examples:

| Scenario | Correct owner |
| --- | --- |
| Repo test command | workspace docs or `AGENTS.md` |
| User prefers concise Chinese answers | NanoMem |
| A reusable workflow skill | local skill filesystem |
| User does not want auto-commits | NanoMem |
| CI job failed with stdout | logs/artifacts |
| User had a negative reaction to auto-commit behavior | NanoMem |
| Screenshot file | filesystem/object store |
| User prefers sketch-based UI discussion | NanoMem, with dialogue evidence |

## 5. Event Facts Are Not Event Logs

NanoMem may store event facts:

```text
The user started designing NanoMem as a long-term personal memory backend.
The user decided that skills should remain in the local filesystem.
The agent changed files without asking and the user objected.
```

NanoMem must not store raw event streams:

```text
The full tool call log for turn abc.
Every file edit made during the current task.
Every message in a chat transcript.
Every CI log line from a failed build.
```

Event facts are useful because they help future agents reason about the user.
Raw event streams belong in harness logs, workspaces, or external systems.

## 6. External Resource Boundary

NanoMem does not directly archive raw external resources such as PDFs, images,
audio, video, screenshots, browser pages, CRM records, or tool outputs.

Allowed capture path:

```text
external resource
  -> agent/tool reads it
  -> assistant final answer or visible summary mentions the relevant fact
  -> NanoMem captures a MemoryUnit from the dialogue
```

Not allowed:

```text
Store or reference the image, PDF, audio, video, screenshot, dataset, browser
dump, or tool result as first-class NanoMem evidence.
```

## 7. Decision Rule

Use this rule when ownership is unclear:

```text
If the agent can reliably reread the information from a workspace, file,
skill store, log system, object store, or business system, do not store it in
NanoMem.

If the information is cross-session, user-related, durable, and useful for
future interaction, store it as a third-person MemoryUnit with dialogue
evidence.
```
