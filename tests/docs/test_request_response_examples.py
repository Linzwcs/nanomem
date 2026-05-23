from __future__ import annotations

import json
from pathlib import Path
import re


EXAMPLE_DOC = Path("docs/reports/request-response-examples.md")
JSON_BLOCK = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


def test_request_response_examples_are_valid_json() -> None:
    text = EXAMPLE_DOC.read_text(encoding="utf-8")
    blocks = JSON_BLOCK.findall(text)

    assert blocks
    for block in blocks:
        payload = json.loads(block)
        assert isinstance(payload, dict)


def test_request_response_examples_use_frozen_owner_and_dialogue_fields() -> None:
    text = EXAMPLE_DOC.read_text(encoding="utf-8")

    assert '"user_id"' not in text
    assert '"events"' not in text
    assert '"owner_id"' in text
    assert '"dialogue"' in text
    assert '"messages"' in text
