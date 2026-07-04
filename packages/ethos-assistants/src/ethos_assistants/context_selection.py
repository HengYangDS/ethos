from __future__ import annotations

import hashlib
from typing import Any

from ethos_core.contracts.context_projection import UNTRUSTED_CONTEXT_LABEL
from ethos_core.contracts.context_projection import (
    default_context_policy as _default_context_policy,
)

FORBIDDEN_RESULT_FIELDS = {
    "instruction_role",
    "role",
    "system",
    "developer",
    "tool_call",
    "tool_calls",
}
QUERY_REDACTION_MARKER = "<redacted-query>"


def default_context_policy() -> dict[str, Any]:
    return _default_context_policy()


def sanitize_selection_result(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key not in FORBIDDEN_RESULT_FIELDS}


def query_digest(query: str) -> str:
    return "sha256:" + hashlib.sha256(query.encode("utf-8")).hexdigest()


def selection_report(
    *,
    query: str,
    results: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]] | None = None,
    manifest_id: str = "manifest:none",
) -> dict[str, object]:
    clean_results = [sanitize_selection_result(result) for result in results]
    verified_count = sum(
        1 for result in clean_results if result.get("verification", {}).get("status") == "verified"
    )
    return {
        "manifest_id": manifest_id,
        "query": QUERY_REDACTION_MARKER,
        "query_digest": query_digest(query),
        "result_count": len(clean_results),
        "verified_count": verified_count,
        "untrusted_context_label": UNTRUSTED_CONTEXT_LABEL,
        "diagnostics": diagnostics or [],
        "results": clean_results,
    }
