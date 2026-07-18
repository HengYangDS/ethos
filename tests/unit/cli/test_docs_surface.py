from __future__ import annotations

from tests.support.ethos_cli_runner import run_ethos


def test_docs_command_uses_registry_for_discovery() -> None:
    payload = run_ethos("docs", "agent-projections", "--json")

    assert payload["ok"] is True
    assert payload["data"]["path"] == "docs/architecture/agent-projections.md"
