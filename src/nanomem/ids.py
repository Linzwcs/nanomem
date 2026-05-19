from __future__ import annotations

import hashlib
import json
from typing import Any

from nanomem.contracts import DialogueRef, MemoryScope


def stable_id(prefix: str, payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def scope_payload(scope: MemoryScope) -> dict[str, Any]:
    return {
        "owner_id": scope.owner_id,
        "namespace": scope.namespace,
    }


def dialogue_ref_payload(ref: DialogueRef) -> dict[str, Any]:
    return {
        "dialogue_id": ref.dialogue_id,
        "message_range": ref.message_range,
    }
