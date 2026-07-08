from __future__ import annotations

from typing import Any

from ethos.assistants.context.selection import selection_report
from ethos_core.contracts.context_projection import CONTEXT_PROJECTION_AUTHORITY
from ethos_core.contracts.context_projection import UNTRUSTED_CONTEXT_LABEL


def context_bundle(
    *,
    query: str | None = None,
    selection: dict[str, Any] | None = None,
    scope: str = "repo",
) -> dict[str, object]:
    bundle: dict[str, object] = {
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
            "ethos://schemas/result": "system/schemas/kernel/result.schema.json",
            "ethos://governance/evolution": "evolution/ledger.toml",
        },
        "rules": [
            "agent hosts consume ETHOS context without becoming truth stores",
            "host-local credentials and sessions stay outside repository truth",
            "protocol adapters expose command JSON, docs, and schemas only",
        ],
    }
    if query is not None or selection is not None:
        raw_query = query or str(selection.get("query", "") if selection else "")
        safe_selection = selection_report(
            query=raw_query,
            results=list(selection.get("results", []) if selection else []),
            diagnostics=list(selection.get("diagnostics", []) if selection else []),
            manifest_id=str(
                selection.get("manifest_id", "manifest:none") if selection else "manifest:none"
            ),
        )
        projection = {
            "truth": "repository",
            "authority": CONTEXT_PROJECTION_AUTHORITY,
            "scope": scope,
            "query": safe_selection["query"],
            "query_digest": safe_selection["query_digest"],
            "untrusted_context_label": UNTRUSTED_CONTEXT_LABEL,
            "selection": safe_selection,
        }
        bundle["context_projection"] = projection
    return bundle
