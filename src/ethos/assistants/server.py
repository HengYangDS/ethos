from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING
from typing import TextIO
from typing import cast

from ethos.assistants.mcp import McpManifest
from ethos.assistants.mcp import mcp_manifest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def mcp_server_descriptor() -> dict[str, object]:
    manifest = mcp_manifest()
    return {
        "protocol": "mcp",
        "transport": "stdio",
        "resources": manifest["resources"],
        "prompts": manifest["prompts"],
        "tools": manifest["tools"],
        "truth": "repository",
        "runtime": "adapter",
    }


def serve_mcp(
    *,
    root: Path | None,
    reader: TextIO,
    writer: TextIO,
    command_runner: Callable[[list[str]], dict[str, object]] | None = None,
) -> None:
    """Serve the fixed, read-only MCP surface over newline-delimited JSON-RPC."""
    runner = command_runner or _command_runner(root)
    for raw in reader:
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            _write(writer, _error(None, -32700, "parse error"))
            continue
        if not isinstance(request, dict):
            _write(writer, _error(None, -32600, "invalid request"))
            continue
        _write(writer, _dispatch(request, root=root, runner=runner))


def _dispatch(
    request: dict[str, object],
    *,
    root: Path | None,
    runner: Callable[[list[str]], dict[str, object]],
) -> dict[str, object]:
    request_id = request.get("id")
    method = request.get("method")
    params = _mapping(request.get("params"))
    manifest = mcp_manifest()
    if not isinstance(method, str):
        response = _error(request_id, -32600, "invalid request")
    elif method == "initialize":
        response = _result(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "ethos", "version": "0"},
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
            },
        )
    elif method == "tools/list":
        response = _result(request_id, {"tools": _tools(manifest)})
    elif method == "tools/call":
        response = _tool_call_response(request_id, params, manifest, runner)
    elif method == "resources/list":
        response = _result(request_id, {"resources": _resources(manifest)})
    elif method == "resources/read":
        response = _resource_read_response(request_id, params, manifest, root)
    elif method == "prompts/list":
        response = _result(request_id, {"prompts": _prompts(manifest)})
    elif method == "prompts/get":
        response = _prompt_get_response(request_id, params, manifest)
    else:
        response = _error(request_id, -32601, "method not found")
    return response


def _tool_call_response(
    request_id: object,
    params: dict[str, object],
    manifest: McpManifest,
    runner: Callable[[list[str]], dict[str, object]],
) -> dict[str, object]:
    name = str(params.get("name") or "")
    tools = manifest["tools"]
    if name not in tools:
        return _error(request_id, -32602, "unknown or non-readonly tool")
    command = tools[name].get("command")
    if not isinstance(command, list) or not all(isinstance(value, str) for value in command):
        return _error(request_id, -32602, "invalid readonly tool")
    payload = runner(cast("list[str]", command))
    return _result(
        request_id,
        {"content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}]},
    )


def _resource_read_response(
    request_id: object,
    params: dict[str, object],
    manifest: McpManifest,
    root: Path | None,
) -> dict[str, object]:
    uri = str(params.get("uri") or "")
    resource = manifest["resources"].get(uri)
    if not isinstance(resource, dict):
        return _error(request_id, -32602, "unknown resource")
    content = _resource_content(resource, root)
    return _result(request_id, {"contents": [{"uri": uri, "text": content}]})


def _prompt_get_response(
    request_id: object, params: dict[str, object], manifest: McpManifest
) -> dict[str, object]:
    name = str(params.get("name") or "")
    prompt = manifest["prompts"].get(name)
    if not isinstance(prompt, dict):
        return _error(request_id, -32602, "unknown prompt")
    return _result(
        request_id,
        {
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": prompt["text"]},
                }
            ]
        },
    )


def _tools(manifest: McpManifest) -> list[dict[str, object]]:
    tools = manifest["tools"]
    return [
        {
            "name": name,
            "description": str(value["capability"]),
            "inputSchema": {"type": "object"},
        }
        for name, value in sorted(tools.items())
    ]


def _resources(manifest: McpManifest) -> list[dict[str, object]]:
    resources = manifest["resources"]
    return [
        {
            "uri": uri,
            "name": uri.rsplit("/", 1)[-1],
            "description": value["description"],
        }
        for uri, value in sorted(resources.items())
    ]


def _prompts(manifest: McpManifest) -> list[dict[str, object]]:
    prompts = manifest["prompts"]
    return [
        {"name": name, "description": value["capability"]}
        for name, value in sorted(prompts.items())
    ]


def _resource_content(resource: dict[str, object], root: Path | None) -> str:
    if "payload" in resource:
        return json.dumps(resource["payload"], sort_keys=True)
    relative = str(resource.get("path") or "")
    if root is None or not relative:
        return ""
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _mapping(value: object) -> dict[str, object]:
    """Return a JSON object as the narrow mapping accepted by this transport."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}


def _command_runner(root: Path | None) -> Callable[[list[str]], dict[str, object]]:
    def run(command: list[str]) -> dict[str, object]:
        args = [sys.executable, "-m", "ethos.cli", *command[1:]]
        if root is not None:
            args.extend(["--root", root.as_posix()])
        completed = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError:
            return {
                "ok": False,
                "stderr": completed.stderr,
                "returncode": completed.returncode,
            }

    return run


def _result(request_id: object, result: dict[str, object]) -> dict[str, object]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: object, code: int, message: str) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _write(writer: TextIO, payload: dict[str, object]) -> None:
    writer.write(json.dumps(payload, sort_keys=True) + "\n")
    writer.flush()
