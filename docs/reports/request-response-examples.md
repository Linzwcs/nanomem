# Request And Response Examples

Status: draft

Date: 2026-05-19

These examples use the current NanoMem JSON contracts. HTTP endpoints accept and
return the same shapes shown here:

- `POST /v1/capture`
- `POST /v1/read`

## 1. Capture Preference

Request:

```json
{
  "capture_time": "2026-05-19T10:00:05+08:00",
  "dialogue": {
    "messages": [
      {
        "content": "I prefer concise Chinese answers. Please remember that I usually want architecture first, then code.",
        "metadata": {},
        "role": "user",
        "speaker_id": "user-demo",
        "timestamp": "2026-05-19T10:00:00+08:00"
      }
    ],
    "metadata": {
      "host": "docs-example"
    },
    "occurred_at": "2026-05-19T10:00:00+08:00"
  },
  "scope": {
    "namespace": "personal",
    "owner_id": "user-demo"
  }
}
```

Response:

```json
{
  "accepted_message_count": 1,
  "dialogue_id": "dlg_98ebcec8fbe85900faafcbf4",
  "skipped": [],
  "stats": {
    "extractor": "heuristic_v1",
    "inserted_unit_count": 2,
    "message_count": 1,
    "skipped_count": 0,
    "unit_count": 2
  },
  "trace_ref": null,
  "unit_count": 2,
  "units": [
    {
      "available_at": "2026-05-19T10:00:05+08:00",
      "dialogue_refs": [
        {
          "dialogue_id": "dlg_98ebcec8fbe85900faafcbf4",
          "message_range": [
            0,
            1
          ]
        }
      ],
      "memory_type": "preference",
      "metadata": {
        "extractor": "heuristic_v1",
        "source_role": "user",
        "speaker_id": "user-demo"
      },
      "redacted_at": null,
      "retention_until": null,
      "scope": {
        "namespace": "personal",
        "owner_id": "user-demo"
      },
      "text": "I prefer concise Chinese answers.",
      "timestamp": "2026-05-19T10:00:00+08:00",
      "unit_id": "unit_73f8c65770c17f9253ecf842"
    },
    {
      "available_at": "2026-05-19T10:00:05+08:00",
      "dialogue_refs": [
        {
          "dialogue_id": "dlg_98ebcec8fbe85900faafcbf4",
          "message_range": [
            0,
            1
          ]
        }
      ],
      "memory_type": "background",
      "metadata": {
        "extractor": "heuristic_v1",
        "source_role": "user",
        "speaker_id": "user-demo"
      },
      "redacted_at": null,
      "retention_until": null,
      "scope": {
        "namespace": "personal",
        "owner_id": "user-demo"
      },
      "text": "Please remember that I usually want architecture first, then code.",
      "timestamp": "2026-05-19T10:00:00+08:00",
      "unit_id": "unit_bdb41289ee2ad308eecd9a0f"
    }
  ]
}
```

## 2. Capture With Skipped Messages

Request:

```json
{
  "capture_time": "2026-05-19T10:05:05+08:00",
  "dialogue": {
    "messages": [
      {
        "content": "README.md says the server command is nanomem-server --config nanomem.json.",
        "metadata": {},
        "role": "user",
        "speaker_id": "user-demo",
        "timestamp": "2026-05-19T10:05:00+08:00"
      },
      {
        "content": "pytest output: 13 passed, 1 skipped.",
        "metadata": {},
        "role": "tool",
        "speaker_id": "shell",
        "timestamp": "2026-05-19T10:05:01+08:00"
      },
      {
        "content": "Please remember that I do not want raw tool logs stored as long-term personal memory.",
        "metadata": {},
        "role": "user",
        "speaker_id": "user-demo",
        "timestamp": "2026-05-19T10:05:02+08:00"
      }
    ],
    "metadata": {
      "host": "docs-example"
    },
    "occurred_at": "2026-05-19T10:05:00+08:00"
  },
  "scope": {
    "namespace": "personal",
    "owner_id": "user-demo"
  }
}
```

Response:

```json
{
  "accepted_message_count": 3,
  "dialogue_id": "dlg_ef68f73b7519337295141013",
  "skipped": [
    {
      "detail": "workspace-local content belongs to local files",
      "message_range": [
        0,
        1
      ],
      "reason": "workspace_fact"
    },
    {
      "detail": null,
      "message_range": [
        1,
        2
      ],
      "reason": "invalid_role"
    }
  ],
  "stats": {
    "extractor": "heuristic_v1",
    "inserted_unit_count": 1,
    "message_count": 3,
    "skipped_count": 2,
    "unit_count": 1
  },
  "trace_ref": null,
  "unit_count": 1,
  "units": [
    {
      "available_at": "2026-05-19T10:05:05+08:00",
      "dialogue_refs": [
        {
          "dialogue_id": "dlg_ef68f73b7519337295141013",
          "message_range": [
            2,
            3
          ]
        }
      ],
      "memory_type": "correction",
      "metadata": {
        "extractor": "heuristic_v1",
        "source_role": "user",
        "speaker_id": "user-demo"
      },
      "redacted_at": null,
      "retention_until": null,
      "scope": {
        "namespace": "personal",
        "owner_id": "user-demo"
      },
      "text": "Please remember that I do not want raw tool logs stored as long-term personal memory.",
      "timestamp": "2026-05-19T10:05:02+08:00",
      "unit_id": "unit_a0ed51ee38ab7722c066a45d"
    }
  ]
}
```

## 3. Read Relevant Memories

Request:

```json
{
  "context_budget_tokens": 512,
  "max_units": 3,
  "metadata": {},
  "namespaces": null,
  "owner_id": "user-demo",
  "query": "answer style architecture first",
  "query_time": "2026-05-19T10:10:00+08:00",
  "recency_policy": null,
  "time_range": null
}
```

Response:

```json
{
  "context": {
    "text": "Relevant memory units:\n- [2026-05-19T10:00:00+08:00, namespace=personal] Please remember that I usually want architecture first, then code.",
    "token_count": 42,
    "unit_count": 1
  },
  "ranked_units": [
    {
      "rank": 1,
      "retrieval_text": "Please remember that I usually want architecture first, then code.",
      "score": 0.38252466449492617,
      "score_breakdown": {
        "dense": 0.17677669529663687,
        "embedding_model": "hashing_embedding_128",
        "recency": 0.9997685720897941,
        "recency_policy": "balanced",
        "relevance": 0.17677669529663687,
        "scan_limit": 2000,
        "scanned_count": 2
      },
      "unit": {
        "available_at": "2026-05-19T10:00:05+08:00",
        "dialogue_refs": [
          {
            "dialogue_id": "dlg_98ebcec8fbe85900faafcbf4",
            "message_range": [
              0,
              1
            ]
          }
        ],
        "memory_type": "background",
        "metadata": {
          "extractor": "heuristic_v1",
          "source_role": "user",
          "speaker_id": "user-demo"
        },
        "redacted_at": null,
        "retention_until": null,
        "scope": {
          "namespace": "personal",
          "owner_id": "user-demo"
        },
        "text": "Please remember that I usually want architecture first, then code.",
        "timestamp": "2026-05-19T10:00:00+08:00",
        "unit_id": "unit_bdb41289ee2ad308eecd9a0f"
      }
    }
  ],
  "request": {
    "context_budget_tokens": 512,
    "max_units": 3,
    "metadata": {},
    "namespaces": null,
    "owner_id": "user-demo",
    "query": "answer style architecture first",
    "query_time": "2026-05-19T10:10:00+08:00",
    "recency_policy": null,
    "time_range": null
  },
  "stats": {
    "candidate_count": 1,
    "context_tokens": 42,
    "index_backend": "dense_cosine_v1",
    "query": "answer style architecture first",
    "ranked_count": 1,
    "ranking_policy": "relevance_recency_v1",
    "recency_policy": "balanced",
    "render_policy": "evidence_context_v1",
    "returned_unit_count": 1,
    "time_range_filter": {
      "end": null,
      "start": null
    }
  },
  "trace_ref": null
}
```

## 4. Read With Namespace Filter

Request:

```json
{
  "context_budget_tokens": null,
  "max_units": 3,
  "metadata": {},
  "namespaces": [
    "work"
  ],
  "owner_id": "user-demo",
  "query": "answer style architecture first",
  "query_time": "2026-05-19T10:10:00+08:00",
  "recency_policy": null,
  "time_range": null
}
```

Response:

```json
{
  "context": {
    "text": "",
    "token_count": 0,
    "unit_count": 0
  },
  "ranked_units": [],
  "request": {
    "context_budget_tokens": null,
    "max_units": 3,
    "metadata": {},
    "namespaces": [
      "work"
    ],
    "owner_id": "user-demo",
    "query": "answer style architecture first",
    "query_time": "2026-05-19T10:10:00+08:00",
    "recency_policy": null,
    "time_range": null
  },
  "stats": {
    "candidate_count": 0,
    "context_tokens": 0,
    "index_backend": "dense_cosine_v1",
    "query": "answer style architecture first",
    "ranked_count": 0,
    "ranking_policy": "relevance_recency_v1",
    "recency_policy": "balanced",
    "render_policy": "evidence_context_v1",
    "returned_unit_count": 0,
    "time_range_filter": {
      "end": null,
      "start": null
    }
  },
  "trace_ref": null
}
```

## 5. Bad Capture Request

Request:

```json
{
  "capture_time": "2026-05-19T10:00:05+08:00",
  "dialogue": {
    "messages": [],
    "occurred_at": "2026-05-19T10:00:00+08:00"
  },
  "scope": {
    "namespace": "personal",
    "owner_id": "user-demo"
  }
}
```

HTTP 400 response:

```json
{
  "detail": "CaptureRequest.dialogue.messages is required",
  "error": "bad_request"
}
```

## Notes

- `namespaces: null` means read all namespaces for the owner.
- `recency_policy: null` lets the service use the configured default,
  currently `balanced`.
- `DialogueRecord` rows are archived internally and referenced by
  `dialogue_refs`; they are not returned by normal `read`.
- Operation logs are append-only diagnostics and are not exposed in normal
  capture/read responses.
