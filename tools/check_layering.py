"""Layering enforcement for the v0.3 horizontal architecture.

Walks every ``.py`` file under ``src/nanomem/`` and verifies that its
imports respect the layer dependency rule:

::

    hosts/        may import from service, transports, admin, pipeline, core
    admin/        may import from service, pipeline, core
    transports/   may import from service, pipeline, core
    service/      may import from pipeline, core
    pipeline/     may import from core
    core/         may only import from stdlib (no other nanomem layers)

The top-level ``src/nanomem/__init__.py`` is exempt (it deliberately
re-exports the full public surface across all layers).

Exit code 0 on clean, 1 on violation. Run as::

    python3 tools/check_layering.py

Violations can be temporarily exempted by adding the comment
``# layering-exception: <reason>`` on the import line. Use sparingly
and file a follow-up issue.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src" / "nanomem"

LAYER_ORDER: tuple[str, ...] = (
    "core",
    "pipeline",
    "service",
    "transports",
    "admin",
    "hosts",
)


# Each layer's allowed downward dependencies (in addition to stdlib).
# "core" has no allowed nanomem dependencies — stdlib only.
ALLOWED: dict[str, frozenset[str]] = {
    "core": frozenset(),
    "pipeline": frozenset({"core"}),
    "service": frozenset({"core", "pipeline"}),
    "transports": frozenset({"core", "pipeline", "service"}),
    "admin": frozenset({"core", "pipeline", "service"}),
    "hosts": frozenset({"core", "pipeline", "service", "transports", "admin"}),
}


def file_layer(path: Path) -> str | None:
    """Return the top-level layer name for a file under src/nanomem/, or None."""
    try:
        rel = path.relative_to(SRC_ROOT)
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    head = parts[0]
    if head in LAYER_ORDER:
        return head
    return None


def import_layer(module: str) -> str | None:
    """Return the top-level layer name an ``import nanomem.X.Y`` targets."""
    if not module.startswith("nanomem."):
        return None
    parts = module.split(".")
    if len(parts) < 2:
        return None
    head = parts[1]
    if head in LAYER_ORDER:
        return head
    return None


def collect_violations() -> list[str]:
    violations: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        layer = file_layer(path)
        if layer is None:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            violations.append(f"{path}: cannot parse ({exc})")
            continue
        allowed_targets = ALLOWED[layer]
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
            elif isinstance(node, ast.Import):
                module = node.names[0].name if node.names else ""
            else:
                continue
            target = import_layer(module)
            if target is None or target == layer:
                continue
            if target in allowed_targets:
                continue
            # Check for an exception comment on the import line.
            line = path.read_text(encoding="utf-8").splitlines()[node.lineno - 1]
            if "# layering-exception" in line:
                continue
            rel = path.relative_to(REPO_ROOT)
            violations.append(
                f"{rel}:{node.lineno}: {layer}/ imports {target}/ "
                f"(not allowed; allowed: {sorted(allowed_targets) or 'stdlib only'})"
            )
    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("Layering violations:")
        for v in violations:
            print(f"  {v}")
        return 1
    print(f"Layering check passed: {len(LAYER_ORDER)} layers, no violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
