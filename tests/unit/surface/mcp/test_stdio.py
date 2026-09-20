"""Exercise root-bound MCP over real stdio without a second application owner."""

import asyncio
import os
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from ethos.domain.adoption import adopt_repository
from ethos.domain.inspection import inspect_repository
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


def test_stdio_discovery_adoption_and_reconnect(tmp_path):
    """Protocol validation must precede effects and preserve native results."""
    root = init_git_repo(tmp_path / "bound")
    foreign = init_git_repo(tmp_path / "foreign")
    before = dict(os.environ), Path.cwd()
    transport = StdioTransport(
        command=sys.executable,
        args=["-B", "-m", "ethos.cli", "mcp", "--root", str(root)],
        cwd=str(tmp_path),
        keep_alive=False,
        env=dict(os.environ),
    )

    async def exercise():
        async with Client(transport, timeout=20) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == {"status", "adopt"}
            for tool in tools.values():
                assert tool.input_schema.get("additionalProperties") is False
                assert not {"root", "actor"} & tool.input_schema.get("properties", {}).keys()
                assert tool.output_schema["type"] == "object"
            for arguments in (
                {"root": str(foreign)},
                {"actor": "foreign"},
                {"apply": "true"},
            ):
                rejected = await client.call_tool("adopt", arguments, raise_on_error=False)
                assert rejected.is_error
                assert not (root / ".ethos").exists()
                assert not (foreign / ".ethos").exists()
            preview = (await client.call_tool("adopt")).structured_content
            assert preview == adopt_repository(root).to_dict()
            head = git(root, "rev-parse", "HEAD")
            exact = {
                "apply": True,
                "authorize": True,
                "expect_head": head,
                "expect_plan_digest": preview["data"]["plan_digest"],
            }
            for override in (
                {"authorize": False},
                {"expect_head": "0" * 40},
                {"expect_plan_digest": "0" * 64},
            ):
                blocked = await client.call_tool("adopt", exact | override)
                assert blocked.structured_content["verdict"] == "block"
                assert not (root / ".ethos").exists()
            applied = (await client.call_tool("adopt", exact)).structured_content
            assert applied["verdict"] == "pass"
            assert applied["data"]["applied"] is True
            paths = [root / name for name in applied["data"]["planned_files"]]
            retained = {path: path.read_bytes() for path in paths}
            stale = await client.call_tool("adopt", exact)
            assert stale.structured_content["verdict"] == "block"
            assert all(path.read_bytes() == value for path, value in retained.items())
        async with Client(transport, timeout=20) as client:
            observed = (await client.call_tool("status")).structured_content
            assert observed == inspect_repository(root).to_dict()
            assert all(path.read_bytes() == value for path, value in retained.items())

    asyncio.run(exercise())
    assert (dict(os.environ), Path.cwd()) == before
    assert not (foreign / ".ethos").exists()
