from __future__ import annotations

import ethos.surface.cli.assistants as assistants_cli
from tests.support.ethos_cli_runner import run_ethos


def test_assistant_mcp_server_command_is_available() -> None:
    payload = run_ethos("assistants", "mcp-server", "--json")

    assert payload["ok"] is True
    assert payload["data"]["server"]["protocol"] == "mcp"


def test_assistant_projection_commands_are_available() -> None:
    manifest = run_ethos("assistants", "mcp-manifest", "--json")
    projections = run_ethos("assistants", "check-projections", "--json")
    doctor = run_ethos("assistants", "doctor", "--json")

    assert manifest["ok"] is True
    assert "ethos.status" in manifest["data"]["manifest"]["tools"]
    assert projections["ok"] is True
    assert projections["data"]["contract"]["truth"] == "repository-source-and-contracts"
    assert doctor["ok"] is True


def test_assistant_mcp_server_serve_mode_delegates_to_stdio_adapter(tmp_path, monkeypatch) -> None:
    observed = {}
    monkeypatch.setattr(assistants_cli, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        assistants_cli,
        "serve_mcp",
        lambda **kwargs: observed.update(kwargs),
    )

    assistants_cli.mcp_server_command(root=tmp_path, serve=True)

    assert observed["root"] == tmp_path
