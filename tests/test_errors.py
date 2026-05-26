from __future__ import annotations

import pytest

from nanomem.core.errors import (
    CaptureError,
    ConfigError,
    ContractError,
    ExtractionError,
    IndexError_,
    NanoMemError,
    RenderError,
    RetrievalError,
    StoreError,
)


def test_all_errors_descend_from_nanomem_error() -> None:
    for cls in (
        ConfigError,
        ContractError,
        StoreError,
        IndexError_,
        RetrievalError,
        RenderError,
        CaptureError,
        ExtractionError,
    ):
        assert issubclass(cls, NanoMemError)


def test_extraction_error_is_capture_error_subclass() -> None:
    assert issubclass(ExtractionError, CaptureError)


def test_index_error_does_not_shadow_builtin_index_error() -> None:
    assert IndexError_ is not IndexError
    assert not issubclass(IndexError_, IndexError)


def test_input_validation_errors_remain_value_errors_for_back_compat() -> None:
    # Pre-refactor callers caught ValueError on bad input. Keep that
    # contract via multiple inheritance for the three "bad input" classes.
    assert issubclass(ConfigError, ValueError)
    assert issubclass(ContractError, ValueError)
    assert issubclass(ExtractionError, ValueError)
    # Non-input errors should NOT be ValueErrors.
    assert not issubclass(StoreError, ValueError)
    assert not issubclass(IndexError_, ValueError)
    assert not issubclass(RenderError, ValueError)
    assert not issubclass(RetrievalError, ValueError)


def test_nanomem_error_can_be_caught_as_exception() -> None:
    with pytest.raises(NanoMemError):
        raise CaptureError("test")
    with pytest.raises(Exception):
        raise ExtractionError("test")


def test_top_level_export_exposes_error_hierarchy() -> None:
    import nanomem

    assert nanomem.NanoMemError is NanoMemError
    assert nanomem.CaptureError is CaptureError
    assert nanomem.ExtractionError is ExtractionError
    assert nanomem.StoreError is StoreError
    assert nanomem.IndexError_ is IndexError_
