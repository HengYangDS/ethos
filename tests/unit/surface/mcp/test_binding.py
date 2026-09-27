"""Check native MCP binding, validation and synchronous effect drainage."""

import asyncio
import threading
from contextlib import suppress

import pytest
from fastmcp import Client

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as candidate_projection
from ethos.domain.adoption import adopt_repository
from ethos.surface.mcp.server import create_server
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import install_fixture_hook_runtime


@pytest.mark.parametrize("timeout", [0.0, -1.0, float("inf"), float("nan")])
def test_mcp_rejects_unbounded_or_nonpositive_deadlines(tmp_path, timeout):
    """No transport starts with a deadline that cannot bound its work."""
    with pytest.raises(ValueError, match="finite and positive"):
        create_server(tmp_path / "absent", create_target=True, timeout_seconds=timeout)
    assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize("parent_kind", ["missing", "file"])
def test_mcp_formation_requires_an_existing_directory_parent(tmp_path, parent_kind):
    """An absent parent or file parent cannot redirect formation effects."""
    parent = tmp_path / "parent"
    if parent_kind == "file":
        parent.write_text("foreign\n", encoding="utf-8")
    target = parent / "new-project"
    with pytest.raises(ValueError, match="formation_parent_unsafe"):
        create_server(target, create_target=True)
    assert not target.exists()


def test_bound_tools_reject_spoofing_and_preserve_results(tmp_path, monkeypatch):
    root = init_git_repo(tmp_path / "bound")
    monkeypatch.setenv("ETHOS_ACTOR", "bound-actor")
    server = create_server(root)
    assert "Read status" in server.instructions

    async def exercise():
        async with Client(server) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == {"status", "plan", "adopt", "land", "publish"}
            for tool in tools.values():
                assert tool.input_schema["additionalProperties"] is False
                assert not {"root", "actor"} & tool.input_schema.get("properties", {}).keys()
                assert tool.output_schema["type"] == "object"
            for arguments in ({"root": str(tmp_path)}, {"actor": "other"}, {"apply": "true"}):
                for name in ("adopt", "land", "publish"):
                    result = await client.call_tool(name, arguments, raise_on_error=False)
                    assert result.is_error
                    assert not (root / ".ethos").exists()
            observed = await client.call_tool("adopt")
            assert observed.structured_content == adopt_repository(root).to_dict()
            evolution = await client.call_tool(
                "adopt", {"evolve_starter": True, "purpose": "Revised project purpose"}
            )
            assert (
                evolution.structured_content
                == adopt_repository(
                    root, evolve_starter=True, purpose="Revised project purpose"
                ).to_dict()
            )
            monkeypatch.setenv("ETHOS_ACTOR", "changed-actor")
            for name in ("adopt", "land", "publish"):
                rejected = await client.call_tool(name, raise_on_error=False)
                assert rejected.is_error
                assert not (root / ".ethos").exists()

    asyncio.run(exercise())


def test_absent_target_mcp_stays_bound_through_formation(tmp_path, monkeypatch):
    """Explicit formation binding admits one absent target without a root override."""
    target = tmp_path / "new-project"
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:formation")
    with pytest.raises(ValueError, match="mcp_root_unavailable"):
        create_server(target)
    monkeypatch.setattr(
        candidate_projection, "install_hook_launchers", install_fixture_hook_runtime
    )
    server = create_server(target, create_target=True)
    assert "Preview adopt with create=true" in server.instructions
    assert "Read status" not in server.instructions

    async def exercise():
        request = {
            "create": True,
            "starter": "foundation",
            "purpose": "Govern a new repository.",
            "author_name": "Test Contributor",
            "author_email": "test@example.invalid",
        }
        async with Client(server) as client:
            preview = (await client.call_tool("adopt", request)).structured_content
            assert preview["verdict"] == "pass"
            assert not target.exists()
            applied = (
                await client.call_tool(
                    "adopt",
                    request
                    | {
                        "apply": True,
                        "authorize": True,
                        "expect_plan_digest": preview["data"]["plan_digest"],
                    },
                )
            ).structured_content
            assert applied["verdict"] == "pass"
            assert target.is_dir()
            status = (await client.call_tool("status")).structured_content
            assert status["data"]["root"] == str(target)
        with pytest.raises(ValueError, match="formation_target_exists"):
            create_server(target, create_target=True)

    asyncio.run(exercise())


def test_absent_target_mcp_rejects_retargeted_parent(tmp_path, monkeypatch):
    """A moved alias cannot redirect a root-bound formation transport."""
    original, foreign = tmp_path / "original", tmp_path / "foreign"
    original.mkdir()
    foreign.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(original, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:formation")
    server = create_server(alias / "new-project", create_target=True)
    alias.unlink()
    alias.symlink_to(foreign, target_is_directory=True)

    async def exercise():
        async with Client(server) as client:
            result = await client.call_tool(
                "adopt",
                {
                    "create": True,
                    "starter": "foundation",
                    "purpose": "Govern a new repository.",
                    "author_name": "Test Contributor",
                    "author_email": "test@example.invalid",
                },
                raise_on_error=False,
            )
            assert result.is_error
            assert not (original / "new-project").exists()
            assert not (foreign / "new-project").exists()

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
