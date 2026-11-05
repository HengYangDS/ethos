"""MCP previews and applies a repository's exit through the one adopt operation."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastmcp import Client

from ethos.adapters.repo.git import current_head
from ethos.surface.mcp.server import create_server
from tests.support.repository_exit import adopted_with_own_hooks

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_mcp_previews_and_applies_an_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The adopt tool's exit is the same exact-request operation as the CLI's."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    monkeypatch.setenv("ETHOS_ACTOR", "bound-actor")
    server = create_server(repo)

    async def exercise() -> tuple[dict, dict]:
        async with Client(server) as client:
            preview = await client.call_tool("adopt", {"exit_repository": True})
            planned = preview.structured_content
            request = {
                "exit_repository": True,
                "apply": True,
                "authorize": True,
                "expect_head": current_head(repo),
                "expect_plan_digest": planned["data"]["plan_digest"],
            }
            applied = await client.call_tool("adopt", request)
            return planned, applied.structured_content

    planned, applied = asyncio.run(exercise())

    assert planned["state"] == "planned", planned
    assert applied["state"] == "applied", applied
    assert not (common / "ethos/runtime/CURRENT").exists()
