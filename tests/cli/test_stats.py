from __future__ import annotations

import io

from nanomem.admin.cli.main import main


def test_stats_command_reports_new_scope_terms() -> None:
    stdout = io.StringIO()

    exit_code = main(["stats", "--db", ":memory:"], stdout=stdout)

    assert exit_code == 0
    output = stdout.getvalue()
    assert "owners: 0" in output
    assert "namespaces: 0" in output
    assert "dialogues: 0" in output
    assert "operation_logs: 0" in output
    assert "index_backend: dense_cosine_v1" in output
