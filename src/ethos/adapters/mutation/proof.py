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
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Any

from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.contracts.plan import PlanIR
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import RepositoryFacts
from ethos.domain.plan import load_proof_contract
from ethos.domain.plan import load_repository_contract
from ethos.repository.policy.gates import adopter_code_correctness_gaps
from ethos.repository.policy.gates import adopter_gate_descriptor_gaps
from ethos.repository.policy.gates import committed_product_default_gate_ids
from ethos.repository.policy.gates import default_gate_ids
from ethos.repository.policy.gates import gate_nodes
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
        if path.is_absolute():
            return path
        common = git_common_dir(root)
        base = Path(common).parent if common else root
        return base / path
    common = git_common_dir(root)
    return Path(common).parent / _DEFAULT_PROOF_DIR if common else root / _DEFAULT_PROOF_DIR


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
    typed = [run for run in runs if isinstance(run, dict)]
    return (
        len(typed) == len(runs)
        and all(
            run.get("verdict") == "passed"
            and (run.get("trust_bearing") is not True or run.get("state") == "proven")
            for run in typed
        )
        and any(run.get("trust_bearing") is True for run in typed)
    )


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
    merged_runs: dict[str, dict[str, Any]] = {}
    sources = (existing.get("runs"), incoming.get("runs"))
    valid_runs = chain.from_iterable(runs for runs in sources if isinstance(runs, list))
    for index, run in enumerate(item for item in valid_runs if isinstance(item, dict)):
        merged_runs[_run_merge_key(run, index)] = run
    merged = {
        "id": str(incoming.get("id") or existing.get("id") or ""),
        "head": head,
        "durability": str(incoming.get("durability") or existing.get("durability") or "local"),
        "runs": list(merged_runs.values()),
    }
    merged["digest"] = _evidence_digest(merged)
    return merged


def proof_plan(
    root: Path,
    *,
    head: str,
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
    changed_paths: tuple[str, ...] = (),
) -> PlanIR:
    """Compile the exact contract-, fact-, and policy-bound proof plan."""
    contract = load_proof_contract(root, tree_ref=head)
    repository = load_repository_contract(root, tree_ref=head)
    nodes, validation_issues = gate_nodes(gate_ids, full=full, root=root, tree_ref=head)
    facts = RepositoryFacts(
        repository=repository.id,
        head=head,
        tree=current_tree(root, head),
        observed_at=datetime.now().astimezone(),
        values={
            "changed_paths": changed_paths,
            "gate_ids": tuple(node.id for node in nodes),
        },
        source_refs=("git:HEAD", "git:HEAD^{tree}"),
    )
    return compile_plan(
        contract,
        facts,
        nodes,
        policy_digest=gate_policy_digest(root, tree_ref=head),
        validation_issues=validation_issues,
    )


def record_executed_proof(
    root: Path,
    evidence: dict[str, Any],
    *,
    plan: PlanIR | None = None,
) -> Path:
    """Persist or extend the executed EvidenceSet for a single HEAD.

    Stores the FULL evidence body (not just a summary) so the record is later
    self-authenticating: its digest is recomputable from its own contents. If a
    valid record already exists for the same HEAD, merge the newly proven gate
    runs into it. This lets agents build promotion-complete proof from short,
    restartable gate batches without weakening the land completeness check.
    """
    if plan is None:
        message = "proof_plan_digest_required"
        raise ValueError(message)
    head = str(evidence.get("head", ""))
    if plan.facts.get("head") != head:
        message = "proof_plan_head_mismatch"
        raise ValueError(message)
    if plan.verdict != "pass":
        message = "proof_plan_not_admitted"
        raise ValueError(message)
    if not _proof_plan_matches(root, head, plan):
        message = "proof_plan_binding_mismatch"
        raise ValueError(message)
    proof_dir = proof_state_dir(root)
    proof_dir.mkdir(parents=True, exist_ok=True)
    path = proof_dir / f"{head}.json"
    existing_record = executed_proof_record(root, head)
    existing_evidence = (
        existing_record.get("evidence")
        if isinstance(existing_record, dict)
        and existing_record.get("plan_digest") == plan.digest()
        and isinstance(existing_record.get("evidence"), dict)
        else None
    )
    sealed_evidence = (
        _merge_same_head_evidence(existing_evidence, evidence)
        if isinstance(existing_evidence, dict)
        else {**evidence, "digest": _evidence_digest(evidence)}
    )
    record = {
        "schema_version": 4,
        "head": head,
        "state": "proven",
        "evidence": sealed_evidence,
        "evidence_digest": sealed_evidence.get("digest", ""),
        "plan": plan.model_dump(mode="json"),
        "plan_digest": plan.digest(),
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


def _promotion_required_gate_ids(root: Path, *, tree_ref: str | None = None) -> tuple[str, ...]:
    """Return the gate ids a promotion proof must fully cover for this root.

    This is the LAND floor: exactly the default (non-full) gate set that
    `ethos prove --execute` runs — verified to equal a real executed proof's
    action_ids. `full=True` adds release-only gates (build/npm-pack/openspec)
    that the land proof legitimately does not carry, so completeness binds to
    the default set, not the full set.
    """
    if tree_ref is not None:
        committed = committed_product_default_gate_ids(root, tree_ref)
        if committed is not None:
            return committed
    return default_gate_ids(full=False, root=root, tree_ref=tree_ref)


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
    # An adopter root whose profile declares NO native code-correctness gates has a
    # proof floor with no tests/lint/types dimension — a contentless proof must not be
    # promotion-worthy. This is a completeness requirement (not an executable gate), so
    # it is surfaced here rather than injected into the executable floor.
    gaps = [
        *adopter_code_correctness_gaps(root, tree_ref=head),
        *adopter_gate_descriptor_gaps(root, tree_ref=head),
    ]
    evidence = record.get("evidence")
    runs = evidence.get("runs") if isinstance(evidence, dict) else None
    required = _promotion_required_gate_ids(root, tree_ref=head)
    present = (
        {run.get("action_id") for run in runs if isinstance(run, dict)}
        if isinstance(runs, list)
        else set()
    )
    if missing := sorted(g for g in required if g not in present):
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
    gaps = list(adopter_gate_descriptor_gaps(root, tree_ref=head))
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


def _json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeError):
        return None
    return payload if isinstance(payload, dict) else None


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
    record = _json_object(path)
    if record is None or record.get("state") != "proven" or record.get("head") != head:
        return None
    evidence = record.get("evidence")
    try:
        plan = PlanIR.model_validate_json(_stable_json(record.get("plan")))
    except ValueError:
        return None
    if plan.facts.get("head") != head:
        return None
    if not _proof_plan_matches(root, head, plan):
        return None
    # (a) the digest must be reproducible from the sealed body. This is tamper-EVIDENCE
    # (a partial edit / wrong-HEAD copy / truncation fails to recompute), NOT tamper-proof:
    # a same-UID forger authoring the whole body computes this sha256 themselves. Unkeyed
    # digest ⇒ local readiness only; real anti-forgery is independent-identity re-execution.
    # (c) Mirror `ethos prove`: every run must be RECORDED as passed, and at least one
    # trust-bearing run marked proven. This mirrors what a real prove would produce, but
    # does not by itself establish the gates truly ran (see module docstring).
    if (
        not isinstance(evidence, dict)
        or evidence.get("head") != head
        or record.get("plan_digest") != plan.digest()
        or not (sealed := str(evidence.get("digest", "")))
        or _evidence_digest(evidence) != sealed
        or not _runs_prove_head(evidence.get("runs"))
    ):
        return None
    return record


def _proof_plan_matches(root: Path, head: str, plan: PlanIR) -> bool:
    values = plan.facts.get("values")
    changed = values.get("changed_paths", ()) if isinstance(values, dict) else ()
    changed_paths = (
        tuple(str(path) for path in changed) if isinstance(changed, list | tuple) else ()
    )
    try:
        expected = proof_plan(
            root,
            head=head,
            gate_ids=tuple(node.id for node in plan.nodes),
            changed_paths=changed_paths,
        )
    except ValueError:
        return False
    return expected.digest() == plan.digest()


def proof_retention_inventory(
    root: Path,
    *,
    reachable_heads: set[str],
    protected_heads: set[str],
) -> dict[str, Any]:
    """Classify HEAD-keyed proof records for conservative retention."""
    proof_dir = proof_state_dir(root)
    groups: dict[str, list[dict[str, Any]]] = {
        "delete_candidates": [],
        "retained": [],
        "invalid": [],
    }
    if not proof_dir.is_dir():
        return groups
    for path in sorted(item for item in proof_dir.iterdir() if item.is_file()):
        item = _proof_retention_item(root, path)
        if "invalid_reason" in item:
            groups["invalid"].append(item)
            continue
        head = str(item["head"])
        reasons = [
            reason
            for present, reason in (
                (head in protected_heads, "protected_head"),
                (head in reachable_heads, "ref_reachable"),
            )
            if present
        ]
        group = "retained" if reasons else "delete_candidates"
        groups[group].append({**item, "reasons": reasons} if reasons else item)
    return groups


def apply_proof_retention(root: Path, candidates: list[dict[str, Any]]) -> list[str]:
    """Delete exact proof candidates after verifying their content digests."""
    proof_dir = proof_state_dir(root).resolve()
    verified: list[tuple[Path, str]] = []
    for candidate in candidates:
        display_path = str(candidate.get("path") or "")
        path = Path(display_path)
        resolved = (path if path.is_absolute() else root / path).resolve()
        if resolved.parent != proof_dir or resolved.name != f"{candidate.get('head', '')}.json":
            message = f"proof_retention_candidate_outside_store:{display_path}"
            raise ValueError(message)
        if not resolved.is_file() or _file_sha256(resolved) != str(candidate.get("sha256") or ""):
            message = f"proof_retention_candidate_drift:{display_path}"
            raise ValueError(message)
        verified.append((resolved, display_path))
    for path, _display_path in verified:
        path.unlink()
    return [display_path for _path, display_path in verified]


def _proof_retention_item(root: Path, path: Path) -> dict[str, Any]:
    display_path = _display_proof_path(root, path)
    base = {
        "path": display_path,
        "sha256": _file_sha256(path),
        "size": path.stat().st_size,
    }
    head = path.stem
    if (
        path.suffix != ".json"
        or len(head) not in {40, 64}
        or any(character not in "0123456789abcdef" for character in head)
    ):
        return {**base, "invalid_reason": "proof_filename_invalid"}
    record = _json_object(path)
    if record is None:
        return {**base, "invalid_reason": "proof_json_invalid"}
    if record.get("head") != head or not isinstance(record.get("schema_version"), int):
        return {**base, "invalid_reason": "proof_record_invalid"}
    return {**base, "head": head, "schema_version": int(record["schema_version"])}


def _display_proof_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
