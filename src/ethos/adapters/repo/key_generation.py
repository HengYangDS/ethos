"""Read the key generation that a repository recorded last, by a redaction or a rebuild attempt.

A redaction records `redaction:private-peer`, and a history rebuild's apply records its attempt as
`observation:rebuild-attempt` under its `rebuild:<id>` key; each body names the generation of the
key it used, never the key. The redaction verb, rebuild readiness and the rebuild apply hold a
supplied key to that last generation, so one repository keeps one key unless a redaction rotates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.contracts.outcome import refuse
from ethos.repository.paradigm.peer_identity import generation

if TYPE_CHECKING:
    from pathlib import Path

REDACTION = "redaction:private-peer"
REBUILD_ATTEMPT = "observation:rebuild-attempt"


def recorded_generation(root: Path) -> object:
    """Return the generation that the last redaction or rebuild attempt recorded, or None."""
    _set_root, members = read_attestation_set(root)
    recorded = sorted(
        (member for member in members if member.predicate in {REDACTION, REBUILD_ATTEMPT}),
        key=lambda member: member.issued_at,
    )
    return recorded[-1].payload.body.get("generation") if recorded else None


def require_generation(root: Path, key: bytes, *, rotate: bool = False) -> None:
    """Refuse a key of another generation than the last recorded one, unless rotating."""
    last = recorded_generation(root)
    if last is not None and last != generation(key) and not rotate:
        refuse("redaction_key_generation_changed")
