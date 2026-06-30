from __future__ import annotations

from ethos_agent.mcp import mcp_manifest


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
