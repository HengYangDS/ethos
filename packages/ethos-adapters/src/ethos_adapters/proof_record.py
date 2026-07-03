"""Proof-record store — HEAD-keyed persistence of executed proof.

The mutation kernel refuses to land/publish unless a proof record exists AT THE
EXACT current HEAD. This turns "only proven evidence may satisfy land/publish"
(proof_policy) from display prose into a runtime precondition of the merge
(tao First Principle #2: failure-blocking moves upstream; #3: a truth store that
cannot be proved is not one).

The record is a generated artifact under .ethos/state/ — ignored, not tracked
truth; it is re-derived by running `ethos prove --execute` at a HEAD.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _proof_dir(root: Path) -> Path:
    return root / ".ethos" / "state" / "proof"


def _proof_path(root: Path, head: str) -> Path:
    return _proof_dir(root) / f"{head}.json"


def record_executed_proof(
    root: Path,
    *,
    head: str,
    evidence_digest: str,
    gate_count: int,
) -> None:
    """Persist a proof record for HEAD after an executed proof passed."""
    directory = _proof_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "head": head,
        "state": "proven",
        "evidence_digest": evidence_digest,
        "gate_count": gate_count,
    }
    _proof_path(root, head).write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )


def executed_proof_record(root: Path, head: str) -> dict[str, object] | None:
    """Return the proof record bound to HEAD, or None when absent/unreadable."""
    path = _proof_path(root, head)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not isinstance(payload, dict) or payload.get("state") != "proven":
        return None
    if str(payload.get("head") or "") != head:
        return None
    return payload
