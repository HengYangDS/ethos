"""Read the key generation that a repository recorded last, by a redaction or a rebuild attempt.

A redaction records `redaction:private-peer`, and a history rebuild's apply records its attempt as
the signature repair's attempt under its `rebuild:<id>` key; each body names the generation of the
key it used, never the key. A repair's own attempt, under any other key, names none and is not
read. The redaction verb, rebuild readiness and the rebuild apply hold a supplied key to that last
generation, so one repository keeps one key unless a redaction rotates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.attestation_lifetime import REBUILD_KEY
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.commit.signature import ATTEMPT
from ethos.contracts.outcome import refuse
from ethos.repository.paradigm.peer_identity import generation

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation

REDACTION = "redaction:private-peer"


def _names_generation(member: Attestation) -> bool:
    return member.predicate == REDACTION or (
        member.predicate == ATTEMPT and member.subject.startswith(REBUILD_KEY)
    )


def recorded_generation(root: Path) -> str | None:
    """Return the generation that the last redaction or rebuild attempt recorded, or None.

    Only no such record means no generation yet: every writer names one, so a last record that
    names none refuses.
    """
    _set_root, members = read_attestation_set(root)
    recorded = sorted(filter(_names_generation, members), key=lambda member: member.issued_at)
    if not recorded:
        return None
    last = recorded[-1].payload.body.get("generation")
    if not isinstance(last, str) or not last:
        refuse("redaction_key_generation_unrecorded")
    return last


def require_generation(root: Path, key: bytes, *, rotate: bool = False) -> None:
    """Refuse a key of another generation than the last recorded one, unless rotating."""
    last = recorded_generation(root)
    if last is not None and last != generation(key) and not rotate:
        refuse("redaction_key_generation_changed")
