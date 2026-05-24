#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SMOKE_DIR="${NANOMEM_SMOKE_DIR:-"$ROOT_DIR/.nanomem/smoke-lancedb-index-$(date +%Y%m%d%H%M%S)"}"

require_lancedb() {
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" python - <<'PY'
import importlib.util
import sys

missing = [
    name for name in ("lancedb", "pyarrow")
    if importlib.util.find_spec(name) is None
]
if missing:
    print(
        "Missing optional LanceDB dependencies: "
        + ", ".join(missing)
        + ". Install with: python -m pip install -e '.[dev,lancedb]'",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY
}

run_smoke() {
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    python - "$SMOKE_DIR" <<'PY'
import json
import sys
from pathlib import Path

from nanomem.config import config_from_mapping
from nanomem.contracts import (
    CaptureDialogue,
    CaptureRequest,
    DialogueMessage,
    MemoryScope,
    ReadRequest,
)
from nanomem.factory import service_from_config

smoke_dir = Path(sys.argv[1])
smoke_dir.mkdir(parents=True, exist_ok=True)
config_payload = {
    "data_dir": str(smoke_dir),
    "store": {
        "backend": "sqlite",
        "path": str(smoke_dir / "nanomem.db"),
    },
    "index": {
        "backend": "lancedb",
        "path": str(smoke_dir / "lancedb"),
        "table": "memory_units",
        "distance_type": "cosine",
        "embedding": {
            "backend": "hashing",
            "dimensions": 64,
        },
    },
    "extraction": {
        "backend": "heuristic",
    },
    "read": {
        "default_recency_policy": "balanced",
        "default_max_units": 10,
    },
}
(smoke_dir / "nanomem.json").write_text(
    json.dumps(config_payload, indent=2, sort_keys=True),
    encoding="utf-8",
)
config = config_from_mapping(config_payload)
scope = MemoryScope(owner_id="lancedb-smoke-user", namespace="personal")
memories = [
    ("2026-05-24T09:00:00+08:00", "I prefer concise Chinese answers."),
    ("2026-05-24T09:01:00+08:00", "I want architecture first, then code."),
    ("2026-05-24T09:02:00+08:00", "I usually ask for sidecar flow explanations."),
    ("2026-05-24T09:03:00+08:00", "I dislike storing workspace logs as memory."),
    ("2026-05-24T09:04:00+08:00", "I need memory retrieval to stay persistent after restart."),
]


def capture(service, occurred_at, content):
    service.capture(
        CaptureRequest(
            scope=scope,
            dialogue=CaptureDialogue(
                occurred_at=occurred_at,
                messages=(
                    DialogueMessage(
                        role="user",
                        speaker_id=scope.owner_id,
                        content=content,
                        timestamp=occurred_at,
                    ),
                ),
                metadata={"host": "lancedb-smoke"},
            ),
            capture_time=occurred_at,
        )
    )


def read(service, query):
    return service.read(
        ReadRequest(
            owner_id=scope.owner_id,
            namespaces=(scope.namespace,),
            query=query,
            query_time="2026-05-24T09:10:00+08:00",
            max_units=5,
        )
    )


service = service_from_config(config)
try:
    for occurred_at, content in memories:
        capture(service, occurred_at, content)
    first = read(service, "concise Chinese answers architecture first")
    assert service.index.document_count() == len(memories)  # type: ignore[attr-defined]
finally:
    service.store.close()  # type: ignore[attr-defined]

config_no_rebuild = config_from_mapping(
    {
        **config_payload,
        "index": {
            **config_payload["index"],
            "rebuild_on_startup": False,
        },
    }
)
restarted = service_from_config(config_no_rebuild)
try:
    persisted = read(restarted, "sidecar flow explanations persistent restart")
    persisted_count = restarted.index.document_count()  # type: ignore[attr-defined]
finally:
    restarted.store.close()  # type: ignore[attr-defined]

reindexed = service_from_config(config)
try:
    reindex = reindexed.reindex()
    rebuilt = read(reindexed, "memory retrieval persistent after restart")
    rebuilt_count = reindexed.index.document_count()  # type: ignore[attr-defined]
finally:
    reindexed.store.close()  # type: ignore[attr-defined]

if first.context.unit_count < 1:
    raise SystemExit("initial LanceDB read returned no context")
if persisted.context.unit_count < 1:
    raise SystemExit("restart LanceDB read returned no context")
if rebuilt.context.unit_count < 1:
    raise SystemExit("reindexed LanceDB read returned no context")
if persisted_count != len(memories):
    raise SystemExit(f"expected {len(memories)} persisted docs, found {persisted_count}")
if rebuilt_count != len(memories):
    raise SystemExit(f"expected {len(memories)} rebuilt docs, found {rebuilt_count}")
if reindex.indexed_unit_count != len(memories):
    raise SystemExit(
        f"expected {len(memories)} reindexed docs, found {reindex.indexed_unit_count}"
    )

print(f"memory_units={len(memories)}")
print(f"initial_context_units={first.context.unit_count}")
print(f"persisted_index_documents={persisted_count}")
print(f"reindexed_documents={rebuilt_count}")
print(f"index_backend={rebuilt.stats['index_backend']}")
PY
}

main() {
  require_lancedb
  echo "NanoMem LanceDB index smoke test"
  echo "repo: $ROOT_DIR"
  echo "work dir: $SMOKE_DIR"
  echo ""
  run_smoke
  echo ""
  echo "Smoke test passed. Artifacts are in $SMOKE_DIR"
}

main "$@"
