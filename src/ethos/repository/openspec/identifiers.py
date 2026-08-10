"""Canonical OpenSpec active Change identifier grammar."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ethos.contracts.semantic import Commitment

LOGICAL_CHANGE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
TEMPORAL_SUFFIX_PATTERN = re.compile(r"-20\d{6}$")


def logical_change_identifier_issue(identifier: str) -> str:
    """Return the stable validation issue for one logical Change ID."""
    if not LOGICAL_CHANGE_ID_PATTERN.fullmatch(identifier):
        return "invalid"
    if TEMPORAL_SUFFIX_PATTERN.search(identifier):
        return "temporal_suffix"
    return ""


def malformed_change_identity_repair_valid(
    *,
    carrier: str,
    old_id: str,
    old_digest: str,
    new: Commitment,
) -> bool:
    """Return whether a target carrier has the exact repaired Change identity.

    Semantic Commitment changes are admitted by the enclosing rebind operation;
    this predicate owns only the carrier/identifier relationship and the
    presence of the exact old-generation digest evidence.
    """
    logical = carrier.removesuffix("/commitment.toml").rsplit("/", 1)[-1]
    dated = re.fullmatch(r"change:20\d{6}-(.+)", old_id)
    return (
        not logical_change_identifier_issue(logical)
        and new.id == f"change:{logical}"
        and re.fullmatch(r"[a-f0-9]{64}", old_digest) is not None
        and old_id != new.id
        and (dated is None or dated.group(1) == logical)
    )
