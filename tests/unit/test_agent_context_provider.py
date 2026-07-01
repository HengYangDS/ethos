from __future__ import annotations

from ethos_assistants.context import context_bundle
from ethos_assistants.server import mcp_server_descriptor


def test_agent_context_bundle_is_agentic_native_but_repository_bounded() -> None:
    bundle = context_bundle()

    assert bundle["truth"] == "repository"
    assert bundle["entrypoints"]["daily"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert "ethos://docs/index" in bundle["resources"]
    assert "mcp" in bundle["protocols"]
    assert "acp" in bundle["protocols"]


def test_mcp_server_descriptor_exports_context_resource() -> None:
    descriptor = mcp_server_descriptor()

    assert "ethos://context/bundle" in descriptor["resources"]
    assert "ethos.context" in descriptor["tools"]
