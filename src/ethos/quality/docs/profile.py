from __future__ import annotations


def docs_quality_profile() -> dict[str, object]:
    return {
        "schema_version": 1,
        "style_goals": ["faithful", "expressive", "elegant"],
        "checks": [
            {
                "id": "front-matter",
                "asset_classes": ["markdown-docs"],
                "dimensions": ["front-matter"],
                "required": ["subject", "role", "state", "relations"],
                "tool_adapter": "ethos-docs-registry",
            },
            {
                "id": "reader-purpose",
                "asset_classes": ["markdown-docs"],
                "dimensions": ["status", "purpose", "see_also"],
                "required": ["Status", "Purpose", "See also"],
                "tool_adapter": "ethos-docs-registry",
            },
            {
                "id": "link-integrity",
                "asset_classes": ["markdown-docs"],
                "dimensions": ["links", "anchors"],
                "required": ["internal-links", "external-links"],
                "tool_adapter": "lychee",
            },
            {
                "id": "glossary",
                "asset_classes": ["markdown-docs"],
                "dimensions": ["terminology", "discoverability"],
                "required": ["docs/reference/glossary.md"],
                "tool_adapter": "ethos-docs-registry",
            },
            {
                "id": "command-examples",
                "asset_classes": ["markdown-docs"],
                "dimensions": ["command-examples"],
                "required": ["known-public-commands", "mutation-boundary"],
                "tool_adapter": "ethos-command-registry",
            },
        ],
    }
