from __future__ import annotations


def mcp_manifest() -> dict[str, object]:
    return {
        "resources": {
            "ethos://docs/index": {
                "description": "ETHOS documentation index",
                "path": "docs/index.md",
            },
            "ethos://schemas/result": {
                "description": "ETHOS result JSON Schema",
                "path": "schemas/ethos/result.schema.json",
            },
        },
        "prompts": {
            "ethos.campaign-review": "Review a campaign against ETHOS self-evolution criteria.",
            "ethos.hypothesis-challenge": (
                "Challenge whether a hypothesis is proven or should retire."
            ),
        },
        "tools": {
            "ethos.status": {"command": ["ethos", "status", "--json"]},
            "ethos.plan": {"command": ["ethos", "plan", "--changed", "--json"]},
            "ethos.prove": {"command": ["ethos", "prove", "--json"]},
            "ethos.explain": {"command": ["ethos", "explain"]},
        },
    }
