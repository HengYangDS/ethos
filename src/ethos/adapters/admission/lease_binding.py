"""Lease-generation binding checks for tracked Work Lane writes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.store.state.lease.projection import integer_value

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def lease_binding_reason(
    *,
    root: Path,
    branch: str,
    lease: dict[str, object],
    actor: str,
    current_head: str,
    commitment_loader: Callable[..., object],
) -> str:
    """Return the first exact Lease coordinate mismatch for one tracked write."""
    expected_head = str(lease.get("expected_head") or "")
    commitment_reason = ""
    try:
        commitment_loader(root, lease=lease)
    except ValueError as exc:
        reason = str(exc)
        commitment_reason = f"{reason}:{branch}" if reason.startswith("lease_base_") else reason
    checks = (
        (not actor, f"invocation_actor_missing:{branch}"),
        (
            actor != str(lease.get("holder_ref") or ""),
            f"lease_holder_mismatch:{branch}",
        ),
        (
            not str(lease.get("lease_id") or "") or integer_value(lease.get("epoch")) < 1,
            f"lease_generation_missing:{branch}",
        ),
        (expected_head != current_head, f"lease_head_stale:{branch}"),
        (bool(commitment_reason), commitment_reason),
    )
    return next((reason for failed, reason in checks if failed), "")
