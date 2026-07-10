"""HEAD-keyed executed-proof records — tamper-evident.

R3 pinned proof to a HEAD-keyed record, but the record was forgeable: any file with
`state=="proven"` and a matching head was accepted, and the stored evidence_digest was
never re-checked — so `echo '{"head":H,"state":"proven"}' > .ethos/state/proof/H.json`
minted a proof `land` would consume.

This module makes the record SELF-AUTHENTICATING. The record stores the full evidence
body (the executed proof-runs: command, exit code, verdict per gate). `executed_proof_
record` REDERIVES the evidence digest from that stored body and rejects the record
unless (a) the recomputed digest equals the sealed digest, (b) the head matches, and
(c) every trust-bearing run actually passed. A hand-written record cannot satisfy (a)
without reproducing the real gate outputs, and cannot satisfy (c) without the gates
having actually passed — so forgery by file-authoring fails.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

from ethos.repository.policy.gates import adopter_code_correctness_gap
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
        "gate_policy_digest": gate_policy_digest(root),
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
    adopter_gap = adopter_code_correctness_gap(root)
    if adopter_gap:
        gaps.append(adopter_gap)
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
    if stored_digest != gate_policy_digest(root):
        gaps.append("proof_policy_digest_stale")
    evidence = record.get("evidence")
    runs = evidence.get("runs") if isinstance(evidence, dict) else None
    gaps.extend(gate_policy_conformance_gaps(runs, root))
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
    # (a) the digest must be reproducible from the sealed body — a forger cannot
    # fabricate it without the real gate outputs.
    sealed = str(evidence.get("digest", ""))
    if not sealed or _evidence_digest(evidence) != sealed:
        return None
    # (c) Mirror `ethos prove`: every run must pass, and at least one trust-bearing
    # run must be proven. Non-trust diagnostic gates may be merely executed, but they
    # cannot fail or stand alone as promotion evidence.
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
