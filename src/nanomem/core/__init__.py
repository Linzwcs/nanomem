"""Core foundations — contracts, errors, ids/time, serde, policies, config.

This package contains only modules that have no upward dependencies.
Any module here must be importable without pulling in
:mod:`nanomem.pipeline`, :mod:`nanomem.service`, :mod:`nanomem.transports`,
:mod:`nanomem.ops`, or :mod:`nanomem.hosts`.

The horizontal-layering rule (enforced by ``tools/check_layering.py``):

::

    hosts/        depends on service, transports, ops, pipeline, core
    ops/          depends on service, pipeline, core
    transports/   depends on service, pipeline, core
    service/      depends on pipeline, core
    pipeline/     depends on core
    core/         only stdlib
"""

from __future__ import annotations
