"""Policy and matching predicates for retrieval and lifecycle.

Today this package only hosts scope-matching helpers (formerly
``nanomem.policies``). Future additions for update / dedup / conflict
policies will live as sibling submodules:

- :mod:`nanomem.policies.scope`      — scope and namespace matching
- (future) ``nanomem.policies.update``    — update-on-write policies
- (future) ``nanomem.policies.dedup``     — append-time dedup policies
- (future) ``nanomem.policies.conflict``  — read-time conflict resolution

The historical ``from nanomem.core.policies import namespace_matches`` and
``from nanomem.core.policies import scope_matches`` import sites continue
to work through this package ``__init__``.
"""

from __future__ import annotations

from nanomem.core.policies.scope import namespace_matches, scope_matches


__all__ = [
    "namespace_matches",
    "scope_matches",
]
