"""Canonical OpenSpec Change identifier and carrier grammar."""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ethos.contracts.semantic import Commitment

LOGICAL_CHANGE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
TEMPORAL_SUFFIX_PATTERN = re.compile(r"-20\d{6}$")
_ACTIVE_COMMITMENT_PATTERN = re.compile(
    r"^openspec/changes/([a-z][a-z0-9]*(?:-[a-z0-9]+)*)/commitment\.toml$"
)
_ARCHIVED_COMMITMENT_PATTERN = re.compile(
    r"^openspec/changes/archive/(20\d{2}-\d{2}-\d{2})-"
    r"([a-z][a-z0-9]*(?:-[a-z0-9]+)*)/commitment\.toml$"
)
_CHANGE_CARRIER_INVALID = "openspec_change_carrier_invalid"
OPEN_SPEC_ARCHIVE_ROOT = "openspec/changes/archive"


def logical_change_identifier_issue(identifier: str) -> str:
    """Return the stable validation issue for one logical Change ID."""
    if not LOGICAL_CHANGE_ID_PATTERN.fullmatch(identifier):
        return "invalid"
    if TEMPORAL_SUFFIX_PATTERN.search(identifier):
        return "temporal_suffix"
    return ""


def active_change_root(change: str) -> str:
    """Return the sole active OpenSpec root for one logical Change."""
    if logical_change_identifier_issue(change):
        raise ValueError(_CHANGE_CARRIER_INVALID)
    return f"openspec/changes/{change}"


def active_change_commitment(change: str) -> str:
    """Return the sole active Commitment carrier for one logical Change."""
    return f"{active_change_root(change)}/commitment.toml"


def active_change_scope(change: str) -> str:
    """Return the recursive material scope for one active Change."""
    return f"{active_change_root(change)}/**"


def archived_change_root(change: str, archived_on: date) -> str:
    """Return the dated immutable OpenSpec root for one logical Change."""
    if logical_change_identifier_issue(change):
        raise ValueError(_CHANGE_CARRIER_INVALID)
    return f"{OPEN_SPEC_ARCHIVE_ROOT}/{archived_on.isoformat()}-{change}"


def archived_change_commitment(change: str, archived_on: date) -> str:
    """Return the dated immutable Commitment carrier for one logical Change."""
    return f"{archived_change_root(change, archived_on)}/commitment.toml"


def parse_change_commitment(carrier: str) -> tuple[str, date | None] | None:
    """Parse one exact active or archived Commitment carrier."""
    if active := _ACTIVE_COMMITMENT_PATTERN.fullmatch(carrier):
        return active[1], None
    archived = _ARCHIVED_COMMITMENT_PATTERN.fullmatch(carrier)
    if archived is None:
        return None
    try:
        archived_on = date.fromisoformat(archived[1])
    except ValueError:
        return None
    return archived[2], archived_on


def archived_change_commitment_matches(carrier: str, change: str) -> bool:
    """Return whether one carrier is the dated archive for the requested Change."""
    parsed = parse_change_commitment(carrier)
    return parsed is not None and parsed[0] == change and parsed[1] is not None


def change_root_from_commitment(carrier: str) -> str:
    """Return the Change root from one valid active or archived Commitment carrier."""
    if parse_change_commitment(carrier) is None:
        raise ValueError(_CHANGE_CARRIER_INVALID)
    return carrier.removesuffix("/commitment.toml")


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
