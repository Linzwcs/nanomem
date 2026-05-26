from __future__ import annotations

from io import StringIO
import json

import pytest

from nanomem.ops.cli.main import main
from nanomem.hosts.plugins.codex import codex_hooks_config, install_codex_hooks


def test_codex_hooks_config_uses_spool_read_and_capture() -> None:
    config = codex_hooks_config()

    submit_hooks = config["hooks"]["UserPromptSubmit"][0]["hooks"]
    stop_hooks = config["hooks"]["Stop"][0]["hooks"]

    assert [item["command"] for item in submit_hooks] == [
        "nanomem-agent-hook spool --host codex",
        "nanomem-agent-hook read --host codex",
    ]
    assert [item["command"] for item in stop_hooks] == [
        "nanomem-agent-hook capture --host codex"
    ]


def test_install_codex_hooks_writes_project_hooks(tmp_path) -> None:
    result = install_codex_hooks(tmp_path)

    hook_path = tmp_path / ".codex" / "hooks.json"
    payload = json.loads(hook_path.read_text(encoding="utf-8"))

    assert result.hook_path == str(hook_path)
    assert result.overwritten is False
    assert payload == codex_hooks_config()


def test_install_codex_hooks_requires_force_to_overwrite(tmp_path) -> None:
    install_codex_hooks(tmp_path)

    with pytest.raises(FileExistsError):
        install_codex_hooks(tmp_path)

    result = install_codex_hooks(tmp_path, force=True)

    assert result.overwritten is True


def test_cli_install_codex_hooks_does_not_require_database(tmp_path) -> None:
    stdout = StringIO()

    code = main(
        ["install-codex-hooks", "--project-dir", str(tmp_path), "--json"],
        stdout=stdout,
    )

    payload = json.loads(stdout.getvalue())
    assert code == 0
    assert payload["hook_path"] == str(tmp_path / ".codex" / "hooks.json")
