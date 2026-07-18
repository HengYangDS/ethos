"""Closeout-intent marker — the official-closeout discrimination signal.

The reference-transaction hook receives only `(root, ref, old, new)`. That is not
enough to tell an official `ethos land --closeout` ref move apart from a raw
`git update-ref refs/heads/dev <candidate_head> <old>` that a user types by hand —
both are byte-identical CAS operations to the same candidate head. Without a
discriminator, blocking raw ref moves would also block the sanctioned closeout, and
admitting the sanctioned closeout would admit the raw one.

This module is that discriminator. Official closeout writes a ONE-SHOT marker just
before its CAS, binding the exact transition (ref/old/new/candidate_head) and the
proof it carries. The hook consumes the marker during `prepared`: a matching,
unexpired, unconsumed marker means "this process started this closeout".

CRITICAL TRUST BOUNDARY (R19): this marker is a LOCAL DISCIPLINE layer, not a trust
root. A same-UID local adversary can forge it. Its job is to stop fat-finger raw git
and tool-discipline bypass, NOT to provide a cryptographic guarantee — that is the
forge/CI protected-ref re-execution's job. So the hook, after consuming a marker,
STILL re-runs every substantive check (fast-forward, == candidate_head, proof
completeness). The marker answers "is this my closeout?"; it never answers "is this
promotion legal?".
"""

from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any

# Marker TTL: a closeout writes the marker immediately before its CAS, so the live
# window is sub-second. A minute is a generous ceiling that still expires a crashed
# closeout's residue quickly rather than leaving a reusable admit token on disk.
_MARKER_TTL = timedelta(minutes=1)
_MARKER_SUBDIR = Path("ethos") / "closeout-intent"
_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class CloseoutTransition:
    """The exact accepted-ref move an official closeout authorizes.

    These four fields always travel together — the marker binds them and the hook
    matches against them — so they are one value, not four parameters.
    """

    ref_name: str
    old_value: str
    new_value: str
    candidate_head: str


@dataclass(frozen=True, slots=True)
class MarkerExpectation:
    """The proof/policy digests a matched marker must carry to authorize the move.

    Empty strings skip that comparison (a caller with no digest to bind). Bundled so
    consume_closeout_intent stays a small, cohesive signature rather than a bag of
    optional digest parameters.
    """

    evidence_digest: str = ""
    gate_policy_digest: str = ""


def _git_path(root: Path, relative: str) -> Path:
    """Resolve a path inside the git dir via `git rev-parse --git-path`.

    A linked worktree's `.git` is a FILE pointing at the real per-worktree git dir, so
    hardcoding `<root>/.git/...` is wrong there. `--git-path` returns the correct
    per-worktree location (mirrors admission.prewrite._git_path).
    """
    completed = subprocess.run(
        ["git", "rev-parse", "--git-path", relative],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return root / ".git" / relative
    path = Path(completed.stdout.strip())
    return path if path.is_absolute() else root / path


def _marker_dir(root: Path) -> Path:
    return _git_path(root, _MARKER_SUBDIR.as_posix())


def _marker_path(root: Path, nonce: str) -> Path:
    return _marker_dir(root) / f"{nonce}.json"


def write_closeout_intent(
    *,
    root: Path,
    transition: CloseoutTransition,
    evidence_digest: str,
    gate_policy_digest: str = "",
) -> dict[str, Any]:
    """Write a one-shot closeout-intent marker and return it.

    Called by official closeout AFTER capturing accepted_old + candidate_head and
    BEFORE the CAS, in a single capture with the values the CAS will use. The marker is
    keyed by an unguessable nonce and carries the exact transition it authorizes so the
    hook can match old/new/candidate_head and reject a marker written for a different
    move. It also carries the proof's evidence_digest and the live gate_policy_digest so
    admission can reject a marker whose bound proof/policy does not match this transition.
    """
    nonce = uuid.uuid4().hex
    created = datetime.now(UTC)
    marker: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "ref_name": transition.ref_name,
        "old_value": transition.old_value,
        "new_value": transition.new_value,
        "candidate_head": transition.candidate_head,
        "evidence_digest": evidence_digest,
        "gate_policy_digest": gate_policy_digest,
        "nonce": nonce,
        "created_at": created.isoformat(),
        "expires_at": (created + _MARKER_TTL).isoformat(),
    }
    path = _marker_path(root, nonce)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(marker, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return marker


def _read_marker(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _is_expired(marker: dict[str, Any], *, now: datetime) -> bool:
    expires_raw = str(marker.get("expires_at", ""))
    if not expires_raw:
        return True
    try:
        expires = datetime.fromisoformat(expires_raw)
    except (ValueError, TypeError):
        return True
    # ETHOS's writer always emits tz-aware UTC (datetime.now(UTC).isoformat()). A
    # parseable-but-naive timestamp is therefore corrupt/adversarial — and comparing it
    # to the aware `now` would raise TypeError and escape as an unhandled crash that
    # bricks every closeout (sweep is the first step of official closeout). Treat any
    # non-aware value as expired so the sweep reclaims it instead of crashing.
    if expires.tzinfo is None:
        return True
    return now >= expires


def clear_closeout_intent(root: Path, nonce: str) -> None:
    """Delete a marker by nonce (idempotent).

    Called on every closeout terminal state — CAS success, hook rejection, CAS failure
    — so a consumed or dead marker never lingers as a reusable admit token. Crash
    residue is caught by the TTL and the stale sweep.
    """
    path = _marker_path(root, nonce)
    path.unlink(missing_ok=True)


def sweep_stale_closeout_intents(root: Path, *, now: datetime | None = None) -> list[str]:
    """Delete every expired marker and return the nonces removed.

    Backstops process crashes between marker write and cleanup: an abandoned marker
    stops being admissible at its TTL, and this sweep reclaims the file. Safe to call
    opportunistically (e.g. at closeout start).
    """
    moment = now or datetime.now(UTC)
    swept: list[str] = []
    marker_dir = _marker_dir(root)
    if not marker_dir.is_dir():
        return swept
    for path in sorted(marker_dir.glob("*.json")):
        marker = _read_marker(path)
        if marker is None or _is_expired(marker, now=moment):
            path.unlink(missing_ok=True)
            swept.append(path.stem)
    return swept


def consume_closeout_intent(
    *,
    root: Path,
    ref_name: str,
    old_value: str,
    new_value: str,
    expect: MarkerExpectation | None = None,
) -> dict[str, Any]:
    """Find and consume the closeout-intent marker matching this exact ref move.

    Returns {"present": bool, "gap": str}. A present, matching, unexpired marker whose
    bound digests match the expected ones is DELETED (one-shot) and reported present with
    no gap. Absence, field mismatch, expiry, or a digest mismatch each map to a distinct
    gap so the caller (ref_move_admission_report) can explain precisely why a raw ref move
    was refused:

      * no matching marker              -> accepted_ref_move_no_closeout_intent    (B1)
      * marker's old/new differ         -> closeout_intent_mismatch                (B4)
      * marker expired                  -> closeout_intent_stale                   (B5)
      * evidence_digest disagrees       -> closeout_intent_evidence_digest_mismatch
      * gate_policy_digest disagrees    -> closeout_intent_policy_digest_mismatch

    An empty expected_* skips that comparison (back-compat / caller has no digest to
    bind). Reuse (B6) falls out of the one-shot delete. Consuming does NOT admit — the
    caller still re-runs FF / == candidate_head / proof completeness / policy digest.
    """
    moment = datetime.now(UTC)
    marker_dir = _marker_dir(root)
    if not marker_dir.is_dir():
        return {"present": False, "gap": "accepted_ref_move_no_closeout_intent"}

    mismatch_seen = False
    for path in sorted(marker_dir.glob("*.json")):
        marker = _read_marker(path)
        if marker is None:
            continue
        if marker.get("ref_name") != ref_name:
            continue
        if marker.get("old_value") != old_value or marker.get("new_value") != new_value:
            mismatch_seen = True
            continue
        # ref/old/new all match this transition.
        if _is_expired(marker, now=moment):
            path.unlink(missing_ok=True)
            return {"present": True, "gap": "closeout_intent_stale"}
        digest_gap = _digest_mismatch_gap(marker, expect or MarkerExpectation())
        path.unlink(missing_ok=True)  # one-shot: consume on the matching read
        return {"present": True, "gap": digest_gap}

    if mismatch_seen:
        return {"present": True, "gap": "closeout_intent_mismatch"}
    return {"present": False, "gap": "accepted_ref_move_no_closeout_intent"}


def _digest_mismatch_gap(marker: dict[str, Any], expect: MarkerExpectation) -> str:
    """Return the digest-mismatch gap for a matched marker, or '' if the bound digests
    agree (or no expectation was supplied)."""
    if expect.evidence_digest and marker.get("evidence_digest") != expect.evidence_digest:
        return "closeout_intent_evidence_digest_mismatch"
    if expect.gate_policy_digest and marker.get("gate_policy_digest") != expect.gate_policy_digest:
        return "closeout_intent_policy_digest_mismatch"
    return ""
