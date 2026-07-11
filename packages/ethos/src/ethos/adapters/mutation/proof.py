"""HEAD-keyed executed-proof records — tamper-EVIDENT, not tamper-PROOF.

R3 pinned proof to a HEAD-keyed record. This module makes the record SELF-DESCRIBING:
it stores the full evidence body (the executed proof-runs: command, exit code, verdict
per gate), and `executed_proof_record` rederives the evidence digest from that stored
body, rejecting the record unless (a) the recomputed digest equals the sealed digest,
(b) the head matches, and (c) every trust-bearing run is recorded as passed.

WHAT THIS DEFENDS AND WHAT IT DOES NOT (read before trusting a proof):

  * Defends (tamper-EVIDENCE): partial edits, bit-rot, a record copied onto a different
    HEAD, a truncated/half-written record, or a stale record whose policy has since moved
    — all fail the recompute and are treated as absent. This is discipline against
    fat-finger, tool-string-mix, and races.

  * Does NOT defend (NOT tamper-PROOF): a same-UID actor who authors a WELL-FORMED record
    from scratch. Checks (a) and (c) are self-referential — the forger writes every
    `run` with `verdict="passed"`, then computes the sha256 over their own body — so a
    hand-authored `.ethos/state/proof/<H>.json` that never ran a real gate is accepted.
    The digest is UNKEYED (plain sha256, not a MAC/signature): it authenticates NOTHING
    against the agent this product exists to govern, which runs as the same UID and can
    write this file.

Therefore a valid local record means only LOCAL READINESS ("this process asserts the
gates passed"), never a prevention/enforcement guarantee. The genuine trust root against
a same-UID adversary is RE-EXECUTION under an independent identity the agent cannot write
(a local independent-identity verifier, or a hosted forge) — see the EnforcementReceipt
path in adapters/admission/evidence/external.py. Consumers of this record MUST NOT surface
it as "enforced"/"prevented"; the honest claim is `local_readiness`.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

from ethos.repository.policy.gates import adopter_code_correctness_gaps
from ethos.repository.policy.gates import adopter_gate_descriptor_gaps
from ethos.repository.policy.gates import default_gate_ids
from ethos.repository.policy.gates import gate_policy_conformance_gaps
from ethos.repository.policy.gates import gate_policy_digest

_DEFAULT_PROOF_DIR = Path(".ethos") / "state" / "proof"
_TEST_PROOF_STATE_DIR_ENV = "ETHOS_TEST_PROOF_STATE_DIR"


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _pytest_state_active() -> bool:
    """Return whether the current process is running under pytest."""
    return bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("PYTEST_XDIST_WORKER"))


def proof_state_dir(root: Path) -> Path:
    """Return the local executed-proof state directory for ``root``.

    Production proof state stays at ``.ethos/state/proof``. Test workers may
    override the physical directory through ``ETHOS_TEST_PROOF_STATE_DIR`` so
    xdist workers do not race over one shared mutable local-state projection.
    The override is ignored outside pytest.
    """
    override = os.environ.get(_TEST_PROOF_STATE_DIR_ENV, "").strip()
    if override and _pytest_state_active():
        path = Path(override).expanduser()
        return path if path.is_absolute() else root / path
    return root / _DEFAULT_PROOF_DIR


def _proof_path(root: Path, head: str) -> Path:
    return proof_state_dir(root) / f"{head}.json"


def _evidence_digest(body: dict[str, Any]) -> str:
    """Recompute the EvidenceSet digest over the sealed body — must match
    ethos.repository.evidence.core.EvidenceSet.from_runs exactly."""
    canonical = {
        "id": body.get("id", ""),
        "head": body.get("head", ""),
        "durability": body.get("durability", "local"),
        "runs": body.get("runs", []),
    }
    return hashlib.sha256(_stable_json(canonical).encode("utf-8")).hexdigest()


def _runs_prove_head(runs: object) -> bool:
    if not isinstance(runs, list) or not runs:
        return False
    trust_bearing_count = 0
    for run in runs:
        if not isinstance(run, dict):
            return False
        if run.get("verdict") != "passed":
            return False
        if run.get("trust_bearing") is True:
            trust_bearing_count += 1
            if run.get("state") != "proven":
                return False
    return trust_bearing_count > 0


def _run_merge_key(run: dict[str, Any], fallback_index: int) -> str:
    """Return the stable key used when merging same-HEAD proof runs."""
    action_id = str(run.get("action_id") or "").strip()
    if action_id:
        return f"action:{action_id}"
    legacy_id = str(run.get("id") or "").strip()
    if legacy_id:
        return f"legacy:{legacy_id}"
    return f"index:{fallback_index}"


def _merge_same_head_evidence(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Merge already-verified and newly-proven evidence for one immutable HEAD.

    The merge is an availability mechanism, not a bypass: the existing record is
    read through ``executed_proof_record`` before this function is called, and the
    incoming evidence is written only by a successful ``ethos prove --execute``.
    Runs are keyed by action id so a later real gate execution refreshes that
    gate's evidence while preserving previously proven gates for the same HEAD.
    """
    head = str(incoming.get("head", ""))
    merged_runs: list[dict[str, Any]] = []
    positions: dict[str, int] = {}
    for source in (existing, incoming):
        runs = source.get("runs") if isinstance(source, dict) else None
        if not isinstance(runs, list):
            continue
        for run in runs:
            if not isinstance(run, dict):
                continue
            key = _run_merge_key(run, len(merged_runs))
            if key in positions:
                merged_runs[positions[key]] = run
            else:
                positions[key] = len(merged_runs)
                merged_runs.append(run)
    merged = {
        "id": str(incoming.get("id") or existing.get("id") or ""),
        "head": head,
        "durability": str(incoming.get("durability") or existing.get("durability") or "local"),
        "runs": merged_runs,
    }
    merged["digest"] = _evidence_digest(merged)
    return merged


def record_executed_proof(root: Path, evidence: dict[str, Any]) -> Path:
    """Persist or extend the executed EvidenceSet for a single HEAD.

    Stores the FULL evidence body (not just a summary) so the record is later
    self-authenticating: its digest is recomputable from its own contents. If a
    valid record already exists for the same HEAD, merge the newly proven gate
    runs into it. This lets agents build promotion-complete proof from short,
    restartable gate batches without weakening the land completeness check.
    """
    head = str(evidence.get("head", ""))
    proof_dir = proof_state_dir(root)
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / f"{head}.json"
    existing_record = executed_proof_record(root, head)
    existing_evidence = (
        existing_record.get("evidence")
        if isinstance(existing_record, dict) and isinstance(existing_record.get("evidence"), dict)
        else None
    )
    sealed_evidence = (
        _merge_same_head_evidence(existing_evidence, evidence)
        if isinstance(existing_evidence, dict)
        else {**evidence, "digest": _evidence_digest(evidence)}
    )
    record = {
        "schema_version": 3,
        "head": head,
        "state": "proven",
        "evidence": sealed_evidence,
        "evidence_digest": sealed_evidence.get("digest", ""),
        # Stamp the policy digest against head's COMMITTED tree so it is a pure function of
        # the proven commit, matching what the reference-transaction hook recomputes when
        # it validates a move to this head from a worktree still holding a different tree.
        # A clean prove lane's HEAD equals its working tree, so this does not change the
        # value on the stamp path; it removes the check-time worktree dependency. An
        # unresolvable head (fake test SHA) falls back to the working tree on both sides.
        "gate_policy_digest": gate_policy_digest(root, tree_ref=head),
    }
    path.write_text(_stable_json(record), encoding="utf-8")
    return path


def _promotion_required_gate_ids(root: Path) -> tuple[str, ...]:
    """Return the gate ids a promotion proof must fully cover for this root.

    This is the LAND floor: exactly the default (non-full) gate set that
    `ethos prove --execute` runs — verified to equal a real executed proof's
    action_ids. `full=True` adds release-only gates (build/npm-pack/openspec)
    that the land proof legitimately does not carry, so completeness binds to
    the default set, not the full set.
    """
    return default_gate_ids(full=False, root=root)


def _runs_cover_required_set(runs: object, required: tuple[str, ...]) -> bool:
    """Return whether the executed runs cover EVERY required gate id.

    A run's `action_id` is the gate id (gate.to_node -> ActionNode(id) ->
    ProofRun(action_id=node.id)). Promotion completeness is set-coverage of the
    required floor, not `trust_bearing_count > 0`: a focused single-gate proof
    (e.g. `prove --gate proof-policy`) does not cover the floor and is rejected.
    """
    if not isinstance(runs, list):
        return False
    present = {run.get("action_id") for run in runs if isinstance(run, dict)}
    return all(gate_id in present for gate_id in required)


def promotion_completeness_gaps(root: Path, head: str) -> list[str]:
    """Return completeness gaps for a promotion at head, or [] if the proof covers
    the required land floor.

    Separate from `executed_proof_record` (record integrity): a proof may be a
    valid, non-forged record yet be a FOCUSED/diagnostic proof that does not cover
    the required gate set. Promotion (land/closeout/push) requires full coverage —
    this closes "proven != required gates passed". Callers already establish record
    validity via executed_proof_record; this adds the completeness dimension.
    """
    record = executed_proof_record(root, head)
    if record is None:
        return []  # integrity/existence handled by the caller's proof_not_proven path
    gaps: list[str] = []
    # An adopter root whose profile declares NO native code-correctness gates has a
    # proof floor with no tests/lint/types dimension — a contentless proof must not be
    # promotion-worthy. This is a completeness requirement (not an executable gate), so
    # it is surfaced here rather than injected into the executable floor.
    gaps.extend(adopter_code_correctness_gaps(root))
    gaps.extend(adopter_gate_descriptor_gaps(root))
    evidence = record.get("evidence")
    runs = evidence.get("runs") if isinstance(evidence, dict) else None
    required = _promotion_required_gate_ids(root)
    if not _runs_cover_required_set(runs, required):
        present = (
            {run.get("action_id") for run in runs if isinstance(run, dict)}
            if isinstance(runs, list)
            else set()
        )
        missing = sorted(g for g in required if g not in present)
        gaps.append(f"proof_incomplete:{','.join(missing)}")
    return gaps


def gate_policy_gaps(root: Path, head: str) -> list[str]:
    """Gaps where a proof's bound policy identity no longer matches the live policy.

    Two dimensions, both defeating a same-UID forgery that satisfies completeness:
      * proof_policy_digest_stale: the record's stored gate_policy_digest differs from
        the digest recomputed for the live required gate set (a gate's canonical command
        or classification changed, or a script gate's content was tampered — B11/B12).
      * proof_gate_not_policy_conformant:<id>: a covering run did not actually run the
        gate's canonical command, or mislabeled trust_bearing/evidence_class (finding B).
    Absence of a record is the caller's proof_not_proven concern (returns []).
    """
    record = executed_proof_record(root, head)
    if record is None:
        return []
    gaps: list[str] = []
    gaps.extend(adopter_gate_descriptor_gaps(root))
    stored_digest = str(record.get("gate_policy_digest", ""))
    # Resolve the LIVE digest against head's COMMITTED tree, not the working tree. The
    # reference-transaction hook validates an accepted-branch move while the accepted
    # worktree still holds the OLD tree (its sync reset runs after the ref move), so a
    # working-tree read would compare the proof's NEW-tree digest against the OLD tree and
    # spuriously flag proof_policy_digest_stale on every gate-policy-changing closeout.
    # Keying on the promoted head makes stamp-time and check-time read the same tree.
    if stored_digest != gate_policy_digest(root, tree_ref=head):
        gaps.append("proof_policy_digest_stale")
    evidence = record.get("evidence")
    runs = evidence.get("runs") if isinstance(evidence, dict) else None
    gaps.extend(gate_policy_conformance_gaps(runs, root, tree_ref=head))
    return gaps


def executed_proof_record(root: Path, head: str) -> dict[str, Any] | None:
    """Return the verified executed-proof record for head, or None if none is VALID.

    Validity is re-derived, never trusted: recompute the evidence digest from the
    stored body and require it to equal the sealed digest, the head to match, and every
    trust-bearing run to have passed. A forged/edited record fails these checks and is
    treated as absent (so the caller falls back to executed_proof_missing).
    """
    path = _proof_path(root, head)
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(record, dict) or record.get("state") != "proven":
        return None
    if record.get("head") != head:
        return None
    evidence = record.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("head") != head:
        return None
    # (a) the digest must be reproducible from the sealed body. This is tamper-EVIDENCE
    # (a partial edit / wrong-HEAD copy / truncation fails to recompute), NOT tamper-proof:
    # a same-UID forger authoring the whole body computes this sha256 themselves. Unkeyed
    # digest ⇒ local readiness only; real anti-forgery is independent-identity re-execution.
    sealed = str(evidence.get("digest", ""))
    if not sealed or _evidence_digest(evidence) != sealed:
        return None
    # (c) Mirror `ethos prove`: every run must be RECORDED as passed, and at least one
    # trust-bearing run marked proven. This mirrors what a real prove would produce, but
    # does not by itself establish the gates truly ran (see module docstring).
    if not _runs_prove_head(evidence.get("runs")):
        return None
    return record


def _proof_carry_package(
    *, source_root: Path, target_root: Path, head: str, source_verified: bool
) -> dict[str, Any]:
    """Common proof-carry boundary fields."""
    return {
        "head": head,
        "source_root": source_root.resolve().as_posix(),
        "target_root": target_root.resolve().as_posix(),
        "truth_boundary": "local-proof-state-projection",
        "mints_proof": False,
        "same_head_only": True,
        "source_verified": source_verified,
        "target_verified": False,
    }


def carry_executed_proof_record(
    *, source_root: Path, target_root: Path, head: str
) -> dict[str, Any]:
    """Carry a verified HEAD-bound proof record between local roots.

    This is a projection of an already self-authenticating proof record, not a new
    proof minting path: the source record must verify first, and the target copy is
    re-read through the same verifier after writing.
    """
    source_record = executed_proof_record(source_root, head)
    source_path = _proof_path(source_root, head)
    target_path = _proof_path(target_root, head)
    base = _proof_carry_package(
        source_root=source_root,
        target_root=target_root,
        head=head,
        source_verified=source_record is not None,
    )
    if source_record is None:
        return {
            "ok": False,
            "state": "skipped",
            "reason": "source-proof-missing-or-invalid",
            **base,
            "required_gaps": ["proof_not_proven"],
        }
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target_path)
    except OSError as exc:
        return {
            "ok": False,
            "state": "failed",
            "reason": exc.__class__.__name__,
            **base,
            "required_gaps": ["proof_not_proven"],
        }
    if executed_proof_record(target_root, head) is None:
        return {
            "ok": False,
            "state": "failed",
            "reason": "target-proof-invalid-after-copy",
            **base,
            "required_gaps": ["proof_not_proven"],
        }
    return {
        "ok": True,
        "state": "carried",
        **base,
        "target_verified": True,
        "source_path": source_path.as_posix(),
        "target_path": target_path.as_posix(),
        "required_gaps": [],
    }


def discard_executed_proof(root: Path, head: str) -> bool:
    """Delete the HEAD-keyed executed-proof record at root, returning whether one existed.

    Used to reclaim a proof pre-placed for a promotion that did not complete (e.g. the
    accepted CAS lost a concurrent race after the proof was carried). The record is inert
    once orphaned — a later ref move to the same head still needs a fresh one-shot
    closeout-intent marker — so this is hygiene, not a safety requirement. Idempotent.
    """
    path = _proof_path(root, head)
    if not path.exists():
        return False
    path.unlink(missing_ok=True)
    return True
