"""Prompt and prompt-schema constants for LLM-based extraction.

Keeping the prompt text and its allowed memory-type vocabulary in a
dedicated module makes it possible to:

- pin a ``prompt_version`` to every extracted memory unit's metadata,
  so future ranking/eval can A/B prompt revisions;
- regression-test prompt changes against fixtures without touching the
  extractor implementation;
- reuse the same vocabulary for non-LLM extractors that want to remain
  schema-compatible.

Bump :data:`LLM_EXTRACTION_PROMPT_VERSION` whenever the prompt body or
the schema in :data:`ALLOWED_MEMORY_TYPES` changes.
"""

from __future__ import annotations


LLM_EXTRACTION_PROMPT_VERSION = "v1"


ALLOWED_MEMORY_TYPES: frozenset[str] = frozenset(
    {
        "preference",
        "correction",
        "habit",
        "background",
        "relationship",
        "user_event",
        "agent_interaction_event",
        "uncertain",
    }
)


LLM_EXTRACTION_PROMPT = """
Extract durable long-term personal memory units from the visible dialogue.

Return JSON only:
{
  "units": [
    {
      "text": "...",
      "message_range": null,
      "memory_type": "preference|correction|habit|background|relationship|user_event|agent_interaction_event|uncertain"
    }
  ],
  "skipped": [
    {"message_range": [0, 1], "reason": "...", "detail": "..."}
  ]
}

Rules:
- Extract only user-related durable personal facts.
- Use third-person, evidence-grounded wording.
- Only the visible extractable messages are provided; do not infer hidden/tool content.
- Do not extract project docs, code facts, logs, current task state, or raw tool output.
- Do not resolve conflicts or synthesize a canonical profile.
- message_range is optional evidence attribution. Use null by default.
- If a unit has precise evidence, message_range may be a valid half-open range over the provided original indexes.
- A non-null message_range must cover only contiguous provided messages; do not span omitted indexes.
""".strip()


__all__ = [
    "ALLOWED_MEMORY_TYPES",
    "LLM_EXTRACTION_PROMPT",
    "LLM_EXTRACTION_PROMPT_VERSION",
]
