"""Shared state constructors for lifecycle contract matrices."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta

from ethos.contracts.coordination import LaneLease


def assert_public_decision(
    report: dict[str, object],
    *,
    verdict: str,
    state: str | None = None,
    gaps: list[str] | None = None,
) -> None:
    """Assert the stable public decision envelope without duplicating projections."""
    assert report["verdict"] == verdict
    assert "ok" not in report
    mutation = report.get("mutation")
    if isinstance(mutation, dict):
        decision = mutation.get("decision")
        if isinstance(decision, dict):
            assert decision["verdict"] == verdict
    if state is not None:
        assert report["state"] == state
    if gaps is not None:
        assert report["required_gaps"] == gaps


def strict_lease(
    *,
    branch: str = "work/example",
    holder: str = "agent:test:case:holder",
    **updates: object,
) -> LaneLease:
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "lane_ref": branch,
        "holder_ref": holder,
        "generation": 1,
        "expires_at": now + timedelta(days=1),
    }
    values.update(updates)
    return LaneLease.model_validate(values)
