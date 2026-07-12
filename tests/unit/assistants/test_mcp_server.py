from __future__ import annotations

import io
import json
from types import SimpleNamespace

import ethos.assistants.server as server
from ethos.assistants.server import serve_mcp


def _run(requests: list[dict[str, object]]) -> list[dict[str, object]]:
    output = io.StringIO()
    serve_mcp(
        root=None,
        reader=io.StringIO("".join(json.dumps(item) + "\n" for item in requests)),
        writer=output,
        command_runner=lambda command: {"command": command, "ok": True},
    )
    return [json.loads(line) for line in output.getvalue().splitlines()]


def test_mcp_stdio_serves_initialize_listing_and_fixed_readonly_tool() -> None:
    responses = _run(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "ethos.status", "arguments": {}},
            },
        ]
    )

    assert responses[0]["result"]["protocolVersion"]
    names = {tool["name"] for tool in responses[1]["result"]["tools"]}
    assert {"ethos.status", "ethos.plan", "ethos.context"} <= names
    assert "ethos.prove" not in names
    assert responses[2]["result"]["content"][0]["type"] == "text"


def test_mcp_stdio_reads_fixed_resources_and_rejects_unknown_or_mutating_tools() -> None:
    responses = _run(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "resources/read",
                "params": {"uri": "ethos://context/bundle"},
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "ethos.publish", "arguments": {}},
            },
            {"jsonrpc": "2.0", "id": 4, "method": "mutation/run", "params": {}},
        ]
    )

    assert responses[0]["result"]["resources"]
    assert responses[1]["result"]["contents"][0]["uri"] == "ethos://context/bundle"
    assert responses[2]["error"]["code"] == -32602
    assert responses[3]["error"]["code"] == -32601


def test_mcp_stdio_covers_protocol_and_prompt_edges() -> None:
    output = io.StringIO()
    reader = io.StringIO(
        "{\n"
        "1\n"
        + "".join(
            json.dumps(request) + "\n"
            for request in (
                {"jsonrpc": "2.0", "id": 1, "method": 7, "params": []},
                {"jsonrpc": "2.0", "id": 2, "method": "prompts/list", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "prompts/get",
                    "params": {"name": "ethos.campaign-review"},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "prompts/get",
                    "params": {"name": "missing"},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "resources/read",
                    "params": {"uri": "missing"},
                },
            )
        )
    )
    serve_mcp(
        root=None,
        reader=reader,
        writer=output,
        command_runner=lambda command: {"command": command},
    )
    responses = [json.loads(line) for line in output.getvalue().splitlines()]

    assert [response["error"]["code"] for response in responses[:3]] == [-32700, -32600, -32600]
    assert responses[3]["result"]["prompts"]
    assert responses[4]["result"]["messages"][0]["role"] == "user"
    assert responses[5]["error"]["code"] == -32602
    assert responses[6]["error"]["code"] == -32602


def test_mcp_server_refuses_bad_manifest_and_constrains_resources(tmp_path, monkeypatch) -> None:
    manifest = server.mcp_manifest()
    monkeypatch.setattr(
        server,
        "mcp_manifest",
        lambda: {
            **manifest,
            "tools": {"ethos.status": {"capability": "mcp_tool_readonly", "command": "bad"}},
        },
    )
    response = _run(
        [{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ethos.status"}}]
    )
    assert response[0]["error"]["code"] == -32602

    resource_content = server._resource_content  # noqa: RUF100, SLF001 - explicit adapter confinement tests
    assert json.loads(resource_content({"payload": {"ok": True}}, tmp_path))["ok"] is True
    assert resource_content({"path": "docs/index.md"}, None) == ""
    assert resource_content({"path": ""}, tmp_path) == ""
    assert resource_content({"path": "../outside"}, tmp_path) == ""
    assert resource_content({"path": "missing"}, tmp_path) == ""
    document = tmp_path / "docs" / "index.md"
    document.parent.mkdir()
    document.write_text("# context\n", encoding="utf-8")
    assert resource_content({"path": "docs/index.md"}, tmp_path) == "# context\n"


def test_mcp_command_runner_returns_json_or_bounded_subprocess_failure(
    tmp_path, monkeypatch
) -> None:
    observed: list[list[str]] = []

    def json_process(arguments, **_kwargs):
        observed.append(arguments)
        return SimpleNamespace(stdout='{"ok": true}', stderr="", returncode=0)

    monkeypatch.setattr(server.subprocess, "run", json_process)
    runner = server._command_runner(tmp_path)  # noqa: RUF100, SLF001 - transport child process is a bounded adapter detail
    assert runner(["ethos", "status", "--json"]) == {"ok": True}
    assert observed[0][-2:] == ["--root", tmp_path.as_posix()]

    assert server._command_runner(None)(["ethos", "status"]) == {"ok": True}  # noqa: RUF100, SLF001 - no-root server mode must not invent a root argument
    assert "--root" not in observed[1]

    monkeypatch.setattr(
        server.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout="not-json", stderr="failed", returncode=7),
    )
    assert runner(["ethos", "status"])["returncode"] == 7
