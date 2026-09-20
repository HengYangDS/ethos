"""Check native MCP binding, validation and synchronous effect drainage."""

import asyncio
import threading
from contextlib import suppress

import pytest
from fastmcp import Client

from ethos.domain.adoption import adopt_repository
from ethos.surface.mcp.server import create_server
from tests.support.governed_repository import init_git_repo


def test_bound_tools_reject_spoofing_and_preserve_results(tmp_path, monkeypatch):
    root = init_git_repo(tmp_path / "bound")
    monkeypatch.setenv("ETHOS_ACTOR", "bound-actor")
    server = create_server(root)

    async def exercise():
        async with Client(server) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == {"status", "adopt"}
            for tool in tools.values():
                assert tool.input_schema["additionalProperties"] is False
                assert not {"root", "actor"} & tool.input_schema.get("properties", {}).keys()
                assert tool.output_schema["type"] == "object"
            for arguments in ({"root": str(tmp_path)}, {"actor": "other"}, {"apply": "true"}):
                result = await client.call_tool("adopt", arguments, raise_on_error=False)
                assert result.is_error
                assert not (root / ".ethos").exists()
            observed = await client.call_tool("adopt")
            assert observed.structured_content == adopt_repository(root).to_dict()
            monkeypatch.setenv("ETHOS_ACTOR", "changed-actor")
            rejected = await client.call_tool("adopt", raise_on_error=False)
            assert rejected.is_error
            assert not (root / ".ethos").exists()

    asyncio.run(exercise())


@pytest.mark.parametrize("boundary", ["cancel", "deadline"])
def test_cancelled_call_drains_before_successor(tmp_path, boundary):
    started, release, finished = threading.Event(), threading.Event(), threading.Event()
    successor = threading.Event()
    server = create_server(tmp_path, timeout_seconds=0.02 if boundary == "deadline" else 30)

    @server.tool
    def blocked() -> dict[str, bool]:
        started.set()
        assert release.wait(5)
        finished.set()
        return {"finished": True}

    @server.tool
    def following() -> dict[str, bool]:
        successor.set()
        return {"previous_finished": finished.is_set()}

    async def exercise():
        async with Client(server) as client:
            first = asyncio.create_task(client.call_tool("blocked", raise_on_error=False))
            try:
                assert await asyncio.to_thread(started.wait, 3)
                if boundary == "cancel":
                    first.cancel()
                second = asyncio.create_task(client.call_tool("following", raise_on_error=False))
                await asyncio.sleep(0.05)
                assert not finished.is_set()
                assert not successor.is_set()
                release.set()
                with suppress(asyncio.CancelledError):
                    result = await first
                    assert result.is_error
                    assert "observe before retry" in str(result.content)
                result = await asyncio.wait_for(second, 3)
                if boundary == "deadline":
                    assert result.is_error
                    result = await client.call_tool("following")
                assert result.structured_content == {"previous_finished": True}
            finally:
                release.set()

    asyncio.run(exercise())
    assert finished.is_set()
