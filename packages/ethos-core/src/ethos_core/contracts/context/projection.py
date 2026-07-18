from __future__ import annotations

import re
from typing import Any

UNTRUSTED_CONTEXT_LABEL = "UNTRUSTED CONTEXT"
CONTEXT_PROJECTION_AUTHORITY = "projection"
ASSISTANT_TRUTH_BOUNDARY = "repository-source-and-contracts"
CONTEXT_PRIVACY_CEILING = "repo_local"
FORBIDDEN_CONTEXT_USES = ("proof", "required_gap_closure", "workflow_ruling")
CONTEXT_RETRIEVAL_SMOKE_QUERIES: tuple[dict[str, object], ...] = (
    {
        "id": "context-projection-label",
        "query": "UNTRUSTED CONTEXT source verified retrieval",
        "expected_paths": ("docs/architecture/context-projection.md",),
    },
    {
        "id": "command-plane-context-index",
        "query": "ethos assistants context-index authorize",
        "expected_paths": ("docs/reference/command-plane.md",),
    },
)
SECRET_LIKE_RE = re.compile(
    r"(?i)("
    r"(api[_-]?key|secret|password|token|bearer)\s*[:= ]\s*"
    r"['\"]?[A-Za-z0-9_./+=:-]{12,}"
    r"|sk[-_](test|live|proj)[-_][A-Za-z0-9_./+=:-]{12,}"
    r"|ghp_[A-Za-z0-9_]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r")"
)


def default_context_policy() -> dict[str, Any]:
    return {
        "id": "default",
        "privacy_ceiling": CONTEXT_PRIVACY_CEILING,
        "allowed_source_kinds": [
            "tracked_file",
            "claim",
            "dated_evidence",
            "openspec",
            "schema",
            "python_symbol",
        ],
        "forbidden_uses": list(FORBIDDEN_CONTEXT_USES),
        "max_results": 10,
        "max_context_bytes": 12000,
    }


def context_projection_contract() -> dict[str, Any]:
    return {
        "authority": CONTEXT_PROJECTION_AUTHORITY,
        "untrusted_context_label": UNTRUSTED_CONTEXT_LABEL,
        "privacy_ceiling": CONTEXT_PRIVACY_CEILING,
        "can_close_required_gaps": False,
        "can_satisfy_proof": False,
        "forbidden_uses": list(FORBIDDEN_CONTEXT_USES),
    }


def looks_secret_like(text: str) -> bool:
    return bool(SECRET_LIKE_RE.search(text))


def redact_secret_like(text: str) -> str:
    return SECRET_LIKE_RE.sub("<redacted-secret>", text)


def context_retrieval_smoke_queries() -> tuple[dict[str, object], ...]:
    return CONTEXT_RETRIEVAL_SMOKE_QUERIES
