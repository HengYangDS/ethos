"""Closeout-intent marker — the official-closeout discrimination signal.

The reference-transaction hook receives only `(root, ref, old, new)`. That is not
enough to tell an official `ethos land --closeout` ref move apart from a raw
`git update-ref refs/heads/dev <candidate_head> <old>` that a user types by hand —
both are byte-identical CAS operations to the same candidate head. Without a
discriminator, blocking raw ref moves would also block the sanctioned closeout, and
admitting the sanctioned closeout would admit the raw one.

This module is that discriminator. Official closeout writes a ONE-SHOT marker just
before its CAS, binding the exact transition (ref/old/new) and the
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
import os
import uuid
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.repo.git_effect_attestation
from ethos.adapters.mutation.proof import proof_evidence_digest
from ethos.adapters.mutation.proof import proof_plan_for_attestation
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_effects import git_effect_attestations
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from ethos.contracts.plan import TransitionPlan

# Marker TTL: a closeout writes the marker immediately before its CAS, so the live
# window is sub-second. A minute is a generous ceiling that still expires a crashed
# closeout's residue quickly rather than leaving a reusable admit token on disk.
_MARKER_TTL = timedelta(minutes=1)
_MARKER_SUBDIR = Path("ethos") / "closeout-intent"
_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class MarkerExpectation:
    """The proof bindings checked by the one-shot closeout discriminator.

    Marker consumption skips an absent evidence or policy comparison. The TransitionPlan,
    not this local marker, owns effect authority and semantic closure.
    """

    evidence_digest: str = ""
    gate_policy_digest: str = ""


def _git_path(root: Path, relative: str) -> Path:
    """Resolve a path inside the git dir via `git rev-parse --git-path`.

    A linked worktree's `.git` is a FILE pointing at the real per-worktree git dir, so
    hardcoding `<root>/.git/...` is wrong there. `--git-path` returns the correct
    per-worktree location (mirrors admission.prewrite._git_path).
    """
    resolved = git_stdout(root, "rev-parse", "--git-path", relative)
    if not resolved:
        return root / ".git" / relative
    path = Path(resolved)
    return path if path.is_absolute() else root / path


def closeout_intent_dir(root: Path) -> Path:
    return _git_path(root, _MARKER_SUBDIR.as_posix())


def _marker_path(root: Path, nonce: str) -> Path:
    return closeout_intent_dir(root) / f"{nonce}.json"


def write_closeout_intent(
    *,
    root: Path,
    ref_name: str,
    update: GitRefUpdate,
    evidence_digest: str,
    gate_policy_digest: str = "",
) -> dict[str, Any]:
    """Write a one-shot closeout-intent marker and return it.

    Called by official closeout AFTER capturing the expected and desired ref values and
    BEFORE the CAS, in a single capture with the values the CAS will use. The marker is
    keyed by an unguessable nonce and carries the exact transition it authorizes so the
    hook can match old/new and reject a marker written for a different
    move. It also carries the proof's evidence_digest and the live gate_policy_digest so
    admission can reject a marker whose bound proof/policy does not match this transition.
    """
    nonce = uuid.uuid4().hex
    created = datetime.now(UTC)
    marker: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "ref_name": ref_name,
        "old_value": update.expected,
        "new_value": update.desired,
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
    marker_dir = closeout_intent_dir(root)
    if not marker_dir.is_dir():
        return swept
    for path in sorted(marker_dir.glob("*.json")):
        marker = _read_marker(path)
        if marker is None or _is_expired(marker, now=moment):
            path.unlink(missing_ok=True)
            swept.append(path.stem)
    return swept


def execute_closeout_effect(
    *,
    root: Path,
    plan: TransitionPlan,
) -> Attestation:
    """Execute one effect while its exact closeout intents are live."""
    effect = git_effect_from_plan(plan)
    expectation = _proof_expectation(root, plan, effect)
    intents = []
    try:
        intents.extend(
            write_closeout_intent(
                root=root,
                ref_name=ref_name,
                update=update,
                evidence_digest=expectation.evidence_digest,
                gate_policy_digest=expectation.gate_policy_digest,
            )
            for ref_name, update in effect.updates.items()
        )
        attestation = execute_git_effect(
            root,
            plan,
            issuer=os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos",
            attestations=git_effect_attestations(root, effect),
        )
        git_effect_attestations(root, effect, attestation)
        return attestation
    finally:
        for intent in intents:
            clear_closeout_intent(root, str(intent["nonce"]))


def _proof_expectation(root: Path, plan: TransitionPlan, effect) -> MarkerExpectation:
    proof_set = plan.prior_attestations.get("proof_set")
    try:
        proof = Attestation.model_validate_json(
            json.dumps(mutable_json(plan.prior_attestations["proof"]))
        )
        proof_plan_for_attestation(root, proof)
    except (KeyError, TypeError, ValueError) as error:
        message = f"git_effect_prior_proof_invalid:{error}"
        raise ValueError(message) from error
    proof_head = proof.subject.removeprefix("git:commit:")
    if (
        not isinstance(proof_set, str)
        or not proof_set
        or proof_evidence_digest(root, proof_head) != proof_set
    ):
        message = "git_effect_prior_proof_set_mismatch"
        raise ValueError(message)
    if {update.desired for update in effect.updates.values()} != {proof_head}:
        message = "git_effect_prior_proof_head_mismatch"
        raise ValueError(message)
    accepted_payload = plan.prior_attestations.get("accepted_effect")
    if accepted_payload is not None:
        try:
            accepted = Attestation.model_validate_json(json.dumps(mutable_json(accepted_payload)))
            accepted_plan = ethos.adapters.repo.git_effect_attestation.plan_from_attestation(
                accepted
            )
            accepted_effect = git_effect_from_plan(accepted_plan)
            ethos.adapters.repo.git_effect_attestation.validate(
                root,
                accepted_effect,
                accepted,
                issuer=accepted.verifier,
                plan=accepted_plan,
            )
        except (TypeError, ValueError) as error:
            message = f"git_effect_prior_accepted_effect_invalid:{error}"
            raise ValueError(message) from error
        if {
            ref: update.desired for ref, update in accepted_effect.updates.items()
        } != effect.assertions:
            message = "git_effect_prior_accepted_effect_mismatch"
            raise ValueError(message)
    return MarkerExpectation(
        evidence_digest=proof_set,
        gate_policy_digest=proof.policy_digest,
    )


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

    An empty expected_* skips that comparison when the caller has no digest to bind.
    Reuse (B6) falls out of the one-shot delete. Consuming does NOT admit — the
    caller still re-runs FF / candidate-head / proof completeness / policy checks.
    """
    moment = datetime.now(UTC)
    marker_dir = closeout_intent_dir(root)
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
