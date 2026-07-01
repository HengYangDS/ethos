from __future__ import annotations

from ethos_assistants.context import context_bundle


def mcp_manifest() -> dict[str, object]:
    return {
        "resources": {
            "ethos://context/bundle": {
                "description": "ETHOS agentic context bundle",
                "capability": "mcp_resource",
                "payload": context_bundle(),
            },
            "ethos://docs/index": {
                "description": "ETHOS documentation index",
                "capability": "mcp_resource",
                "path": "docs/index.md",
            },
            "ethos://schemas/result": {
                "description": "ETHOS result JSON Schema",
                "capability": "mcp_resource",
                "path": "schemas/ethos/result.schema.json",
            },
        },
        "prompts": {
            "ethos.campaign-review": {
                "capability": "mcp_prompt",
                "text": "Review a campaign against ETHOS evolution criteria.",
            },
            "ethos.hypothesis-challenge": {
                "capability": "mcp_prompt",
                "text": "Challenge whether a hypothesis is proven or should retire.",
            },
        },
        "tools": {
            "ethos.status": {
                "capability": "mcp_tool_readonly",
                "command": ["ethos", "status", "--json"],
            },
            "ethos.plan": {
                "capability": "mcp_tool_readonly",
                "command": ["ethos", "plan", "--changed", "--json"],
            },
            "ethos.prove": {
                "capability": "mcp_tool_proof",
                "command": ["ethos", "prove", "--json"],
            },
            "ethos.explain": {
                "capability": "mcp_tool_readonly",
                "command": ["ethos", "explain"],
            },
            "ethos.context": {
                "capability": "mcp_tool_readonly",
                "command": ["ethos", "assistants", "context", "--json"],
            },
        },
    }
