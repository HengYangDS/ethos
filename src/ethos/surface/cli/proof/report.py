"""Project proof scope, executed checks, and compact context for readers."""

from __future__ import annotations

from typing import cast

from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence

KNOWN_PROOF_SCOPES = frozenset(
    {"repository", "change", "proof-kernel", "code", "docs", "openspec", "quality"}
)


def proof_scope_binding(scope: str) -> dict[str, object]:
    """Return the proof-scope binding for command payloads."""
    normalized = " ".join(scope.split()) or "repository"
    known = normalized in KNOWN_PROOF_SCOPES
    return {
        "scope": normalized,
        "accepted": known,
        "known": known,
        "known_scopes": sorted(KNOWN_PROOF_SCOPES),
        "semantics": "repository is terminal readiness; other scopes are focused evidence",
        "required_gaps": [] if known else [f"unknown_proof_scope:{normalized}"],
    }


def summarize_checks(checks: list[dict[str, object]]) -> list[dict[str, object]]:
    """Project proof checks without embedding diagnostic payloads in command output."""
    return [
        {
            "action_id": check["action_id"],
            "command": check["command"],
            "exit_code": check["exit_code"],
            "verdict": check["verdict"],
            "evidence_class": check["evidence_class"],
            "trust_bearing": check["trust_bearing"],
            "diagnostic_count": len(cast("list[object]", check["diagnostics"])),
            "started_after_seconds": check.get("started_after_seconds"),
            "duration_seconds": check.get("duration_seconds"),
        }
        for check in checks
    ]


def compact_proof_context(
    audit: dict[str, object], lifecycle: dict[str, object]
) -> dict[str, object]:
    """Project bounded audit and lifecycle summaries without their full evidence bodies."""
    audit_openspec = cast("dict[str, object]", audit.get("openspec") or {})
    lifecycle_summary = cast("dict[str, object]", lifecycle.get("summary") or {})
    lifecycle_change_count = lifecycle_summary.get("change_count")
    return {
        "audit": {
            "verdict": report_verdict(audit),
            "mode": str(audit.get("mode") or ""),
            "openspec_mode": str(audit_openspec.get("mode") or ""),
            "required_gap_count": len(string_sequence(audit.get("required_gaps"))),
        },
        "openspec_lifecycle": {
            "verdict": report_verdict(lifecycle),
            "change": str(lifecycle.get("change") or ""),
            "schema_name": str(lifecycle.get("schema_name") or ""),
            "change_count": (
                lifecycle_change_count if isinstance(lifecycle_change_count, int) else 0
            ),
            "required_gaps": list(string_sequence(lifecycle.get("required_gaps"))),
        },
    }
