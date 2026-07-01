from __future__ import annotations

from ethos_assistants.server import mcp_server_descriptor


def test_mcp_server_descriptor_is_protocol_native() -> None:
    descriptor = mcp_server_descriptor()

    assert descriptor["protocol"] == "mcp"
    assert descriptor["transport"] == "stdio"
    assert "ethos://docs/index" in descriptor["resources"]
    assert "ethos.status" in descriptor["tools"]
