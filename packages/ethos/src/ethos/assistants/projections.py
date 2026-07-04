from __future__ import annotations


def projection_contract() -> dict[str, object]:
    return {
        "truth": "repository-source-and-contracts",
        "surfaces": ["codex", "claude", "jetbrains", "mcp", "acp"],
        "rules": [
            "assistant projections are thin adapters",
            "context packs may expose tools but must not become truth stores",
            "MCP and ACP adapters are protocol projections",
        ],
    }
