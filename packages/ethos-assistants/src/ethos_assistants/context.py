from __future__ import annotations


def context_bundle() -> dict[str, object]:
    return {
        "truth": "repository",
        "protocols": ["mcp", "acp"],
        "entrypoints": {
            "daily": [
                "ethos status",
                "ethos plan",
                "ethos prove",
                "ethos land",
                "ethos publish",
            ],
            "governance": [
                "ethos audit",
                "ethos campaign hypotheses",
                "ethos quality release-policy",
                "ethos quality commits",
            ],
        },
        "resources": {
            "ethos://docs/index": "docs/index.md",
            "ethos://docs/command-plane": "docs/reference/command-plane.md",
            "ethos://schemas/result": "schemas/ethos/result.schema.json",
            "ethos://governance/evolution": "docs/governance/evolution-ledger.toml",
        },
        "rules": [
            "agent hosts consume ETHOS context without becoming truth stores",
            "host-local credentials and sessions stay outside repository truth",
            "protocol adapters expose command JSON, docs, and schemas only",
        ],
    }
