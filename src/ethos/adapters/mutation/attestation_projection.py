"""Public command projections for open-predicate Attestations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation


def attestation_payload(attestation: Attestation, *, kind: str) -> dict[str, object]:
    """Add a bounded presentation category without changing semantic identity."""
    payload: dict[str, object] = {
        "kind": kind,
        **attestation.model_dump(mode="json"),
        "mints_authority": False,
    }
    if kind == "effect":
        payload["content"] = payload["statement"]
    return payload
