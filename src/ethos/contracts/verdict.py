"""Closed verdict algebra shared by every decision boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

Verdict = Literal["pass", "block", "unknown"]
_VERDICTS: dict[object, Verdict] = {"pass": "pass", "block": "block", "unknown": "unknown"}


def _items(value: object) -> tuple[object, ...]:
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _has_adverse_diagnostic(value: object) -> bool:
    if not isinstance(value, (list, tuple)):
        return False
    return any(
        isinstance(item, Mapping) and str(item.get("severity", "")).lower() in {"warning", "error"}
        for item in value
    )


def close_verdict(
    verdict: Verdict,
    required_gaps: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> Verdict:
    """Prevent unmet conditions or warnings from remaining a nominal pass."""
    if warnings:
        return "block"
    return "block" if verdict == "pass" and required_gaps else verdict


def observation_verdict(
    *,
    ok: bool | None,
    required_gaps: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> Verdict:
    """Close one local observation without inventing facts for an absent result."""
    candidate: Verdict = "pass" if ok is True else "block" if ok is False else "unknown"
    return close_verdict(candidate, required_gaps, warnings)


def report_verdict(report: Mapping[str, object]) -> Verdict:
    """Reduce one explicit report; an absent or invalid verdict stays unknown."""
    gaps = tuple(str(item) for item in _items(report.get("required_gaps")))
    warnings = (
        ("reported_warning",)
        if _items(report.get("warnings")) or _has_adverse_diagnostic(report.get("diagnostics"))
        else ()
    )
    declared = _VERDICTS.get(report.get("verdict"), "unknown")
    return close_verdict(declared, gaps, warnings)


def reduce_verdicts(
    *verdicts: Verdict,
    required_gaps: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> Verdict:
    """Reduce independent verdicts with block before unknown before pass."""
    candidate: Verdict = (
        "block"
        if "block" in verdicts
        else "unknown"
        if not verdicts or "unknown" in verdicts
        else "pass"
    )
    return close_verdict(candidate, required_gaps, warnings)


def require_closed_verdict(
    verdict: Verdict,
    required_gaps: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> None:
    """Reject a false pass at a typed boundary."""
    if close_verdict(verdict, required_gaps, warnings) != verdict:
        raise ValueError("pass_with_warnings" if warnings else "pass_with_required_gaps")
