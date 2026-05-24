from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


CODEX_HOOKS_RELATIVE_PATH = Path(".codex/hooks.json")


@dataclass(frozen=True)
class CodexHookInstallResult:
    project_dir: str
    hook_path: str
    overwritten: bool


def codex_hooks_config() -> dict[str, Any]:
    return {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "nanomem-agent-hook spool --host codex",
                            "timeout": 5,
                        },
                        {
                            "type": "command",
                            "command": "nanomem-agent-hook read --host codex",
                            "timeout": 5,
                        },
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "nanomem-agent-hook capture --host codex",
                            "timeout": 30,
                        }
                    ]
                }
            ],
        }
    }


def install_codex_hooks(
    project_dir: str | Path = ".",
    *,
    force: bool = False,
) -> CodexHookInstallResult:
    root = Path(project_dir).expanduser().resolve()
    hook_path = root / CODEX_HOOKS_RELATIVE_PATH
    existed = hook_path.exists()
    if existed and not force:
        raise FileExistsError(
            f"{hook_path} already exists; rerun with --force to overwrite it"
        )

    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(
        json.dumps(codex_hooks_config(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return CodexHookInstallResult(
        project_dir=str(root),
        hook_path=str(hook_path),
        overwritten=existed,
    )
