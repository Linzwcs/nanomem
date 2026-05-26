"""LLM-backed memory unit extractor.

This package was previously a single 650-line ``llm.py`` file. The
public surface is unchanged: every name that was importable as
``from nanomem.pipeline.representation.llm import X`` is re-exported here.

Sub-modules:

- :mod:`nanomem.extraction.llm.extractor` — :class:`LLMMemoryUnitExtractor`
- :mod:`nanomem.extraction.llm.client`    — :class:`LLMCompletionClient`
                                            Protocol + OpenAI reference impl
- :mod:`nanomem.extraction.llm.chunking`  — dialogue chunking
- :mod:`nanomem.extraction.llm.parsing`   — payload schema + transform

Prompt text lives in :mod:`nanomem.extraction.prompts` (re-imported
here for ``from nanomem.pipeline.representation.llm import LLM_EXTRACTION_PROMPT``
back-compat).
"""

from __future__ import annotations

from nanomem.pipeline.representation.llm.chunking import (
    DEFAULT_MAX_MESSAGES_PER_CHUNK,
    ExtractionChunk,
)
from nanomem.pipeline.representation.llm.client import (
    LLMCompletionClient,
    OpenAIChatCompletionClient,
)
from nanomem.pipeline.representation.llm.extractor import LLMMemoryUnitExtractor
from nanomem.pipeline.representation.llm.parsing import LLMExtractionPayloadError
from nanomem.pipeline.representation.prompts import (
    ALLOWED_MEMORY_TYPES,
    LLM_EXTRACTION_PROMPT,
    LLM_EXTRACTION_PROMPT_VERSION,
)


__all__ = [
    "ALLOWED_MEMORY_TYPES",
    "DEFAULT_MAX_MESSAGES_PER_CHUNK",
    "ExtractionChunk",
    "LLMCompletionClient",
    "LLMExtractionPayloadError",
    "LLMMemoryUnitExtractor",
    "LLM_EXTRACTION_PROMPT",
    "LLM_EXTRACTION_PROMPT_VERSION",
    "OpenAIChatCompletionClient",
]
