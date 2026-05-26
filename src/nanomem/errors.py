"""Public exception hierarchy for the nanomem package.

Third-party SDK users and integrators should catch ``NanoMemError`` to
catch any library-raised exception. Internal code should raise the most
specific subclass that fits — never bare ``Exception``.

The hierarchy is intentionally shallow:

::

    NanoMemError
      ├─ ConfigError       Bad configuration values or file
      ├─ ContractError     Malformed request shape (HTTP/SDK boundary)
      ├─ StoreError        Persistence layer failure (sqlite, future stores)
      ├─ IndexError_       Index backend failure (trailing underscore avoids
      │                    shadowing the builtin ``IndexError``)
      ├─ RetrievalError    Read-side pipeline failure (rank / filter)
      ├─ RenderError       Evidence rendering failure
      └─ CaptureError      Capture-side pipeline failure
            └─ ExtractionError    Fact-extraction failure (heuristic or LLM)

Adding a new class: subclass the closest existing parent so external
``except NanoMemError`` blocks keep working.
"""

from __future__ import annotations


class NanoMemError(Exception):
    """Base class for every exception raised by the nanomem package."""


class ConfigError(NanoMemError):
    """Invalid configuration value, missing field, or unreadable config file."""


class ContractError(NanoMemError):
    """Request payload violates the public contract (HTTP/SDK boundary).

    Raised when a caller submits a request whose shape, types, or required
    fields do not match the documented contract. Distinct from validation
    failures on otherwise well-shaped data.
    """


class StoreError(NanoMemError):
    """Persistence-layer failure (sqlite or any future MemoryStore backend)."""


class IndexError_(NanoMemError):
    """Index backend failure (lexical, dense, hybrid, lancedb, ...).

    The trailing underscore avoids shadowing the builtin :class:`IndexError`.
    External users should ``from nanomem.errors import IndexError_ as
    NanoMemIndexError`` if a more readable local name is preferred.
    """


class RetrievalError(NanoMemError):
    """Read-side pipeline failure not attributable to a single index/store call."""


class RenderError(NanoMemError):
    """Evidence rendering failure (packing, budget, formatting)."""


class CaptureError(NanoMemError):
    """Capture-side pipeline failure not attributable to extraction alone."""


class ExtractionError(CaptureError):
    """Fact extraction failure (heuristic or LLM extractor)."""


__all__ = [
    "NanoMemError",
    "ConfigError",
    "ContractError",
    "StoreError",
    "IndexError_",
    "RetrievalError",
    "RenderError",
    "CaptureError",
    "ExtractionError",
]
