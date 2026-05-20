from __future__ import annotations

import pytest

from nanomem.config import config_from_mapping
from nanomem.extraction.llm import LLMMemoryUnitExtractor
from nanomem.factory import extractor_from_config


def test_llm_extraction_config_requires_model() -> None:
    config = config_from_mapping(
        {
            "extraction": {
                "backend": "llm",
            }
        }
    )

    with pytest.raises(ValueError, match="llm extraction requires model"):
        extractor_from_config(config)


def test_llm_extraction_config_builds_extractor_with_threshold() -> None:
    config = config_from_mapping(
        {
            "extraction": {
                "backend": "llm",
                "model": "test-model",
                "fallback_backend": "heuristic",
                "confidence_threshold": 0.5,
                "strict_schema": False,
                "max_messages_per_chunk": 6,
                "max_chars_per_chunk": 2000,
            }
        }
    )

    extractor = extractor_from_config(config)

    assert isinstance(extractor, LLMMemoryUnitExtractor)
    assert extractor.confidence_threshold == 0.5
    assert extractor.strict_schema is False
    assert extractor.max_messages_per_chunk == 6
    assert extractor.max_chars_per_chunk == 2000
    assert extractor.fallback is not None


def test_llm_extraction_config_rejects_unknown_fallback_backend() -> None:
    config = config_from_mapping(
        {
            "extraction": {
                "backend": "llm",
                "model": "test-model",
                "fallback_backend": "other",
            }
        }
    )

    with pytest.raises(ValueError, match="Unsupported extraction fallback backend"):
        extractor_from_config(config)


def test_llm_extraction_config_parses_strict_schema_string_false() -> None:
    config = config_from_mapping(
        {
            "extraction": {
                "backend": "llm",
                "model": "test-model",
                "strict_schema": "false",
            }
        }
    )

    assert config.extraction.strict_schema is False
