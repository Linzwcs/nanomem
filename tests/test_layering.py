from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER = REPO_ROOT / "tools" / "check_layering.py"


def test_layering_check_passes() -> None:
    """The v0.3 horizontal-layering rule must hold for every module under src/.

    Run: ``python3 tools/check_layering.py``

    If this test starts failing, you have introduced an upward import
    (e.g. ``pipeline/`` importing from ``service/``). Either:

    1. Move the offending module to a higher layer; or
    2. Add ``# layering-exception: <reason>`` to the import line and
       document why the exception is justified.
    """
    result = subprocess.run(
        [sys.executable, str(CHECKER)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"Layering check failed:\n{result.stdout}\n{result.stderr}"
    )
