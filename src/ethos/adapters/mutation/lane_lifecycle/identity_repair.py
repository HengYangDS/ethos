"""Same-tree commit identity replacement across the local integration train."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import cast

from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.commit_identity import equivalent_commit_identity
from ethos.adapters.repo.commit_identity import verify_commit_trust
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_ref_worktrees import ref_worktree_paths
from ethos.adapters.repo.git_ref_worktrees import sync_ref_worktrees
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.adapters.repo.git_signing import commit_metadata
from ethos.adapters.repo.git_signing import create_signed_commit_replacements
from ethos.adapters.repo.git_signing import existing_commit_replacement
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.lease.lifecycle.transitions import advance_lease_ref
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import integer


def derive_identity_repair_suffix(*, root: Path, base_commit: str) -> dict[str, object]:
    """Derive one immutable exact-CAS receipt for a linear identity-only suffix."""
    repo = repository_root(root)
    status = workspace_status(repo, include_foreign_path_scope=False)
    branch = str(status.get("branch") or "")
    head = current_tracked_head(repo)
    lease = leases_by_branch(repo).get(branch, {})
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    proof = proof_attestation(repo, head)
    gaps = [
        gap
        for valid, gap in (
            (status.get("role") == ROLE_WORK_LANE, "work_lane_required"),
            (not status.get("dirty"), "work_lane_dirty"),
            (bool(actor), "invocation_actor_missing"),
            (lease.get("lease_state") == "valid", f"work_lane_lease_invalid:{branch}"),
            (actor == str(lease.get("holder_ref") or ""), "lease_actor_mismatch"),
            (head == str(lease.get("expected_head") or ""), "lease_head_stale"),
            (
                current_tree(repo, head) == str(lease.get("expected_tree") or ""),
                "lease_expected_tree_stale",
            ),
            (proof is not None, (proof_gaps(repo, head) or ["proof_not_proven"])[0]),
        )
        if not valid
    ]
    if gaps:
        return _suffix_report(branch, base_commit, head, gaps)
    proof = cast("Attestation", proof)
    try:
        replacements = (
            [existing_commit_replacement(repo, base_commit, head)]
            if equivalent_commit_identity(repo, base_commit, head)
            else create_signed_commit_replacements(
                repo, base_commit, _linear_suffix(repo, base_commit, head)
            )
        )
    except ValueError as error:
        gaps.append(str(error))
        return _suffix_report(branch, base_commit, head, gaps)
    mapping = {str(item["old_commit"]): str(item["new_commit"]) for item in replacements}
    train, train_gaps = _suffix_train_refs(repo, branch, mapping)
    gaps.extend(train_gaps)
    if gaps:
        return _suffix_report(branch, base_commit, head, gaps)
    refs = {ref: {"expected": old, "desired": mapping[old]} for ref, old in train.items()}
    request = {
        "schema_version": 1,
        "kind": "identity-repair-suffix-request",
        "branch": branch,
        "actor": actor,
        "base_commit": base_commit,
        "head": head,
        "tree": current_tree(repo, head),
        "lease_generation": lease_generation(lease),
        "proof": proof.model_dump(mode="json"),
        "commits": replacements,
        "refs": refs,
    }
    receipt_payload = {
        "schema_version": 1,
        "kind": "identity-repair-suffix-receipt",
        "request": request,
    }
    receipt_payload["digest"] = hashlib.sha256(_canonical_json(receipt_payload)).hexdigest()
    payload = _canonical_json(receipt_payload)
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    path = _identity_repair_receipt_store(repo) / f"{payload_sha256}.json"
    write_content_addressed(path, payload, collision="identity_repair_receipt_collision")
    return {
        "verdict": "pass",
        "state": "derived",
        "branch": branch,
        "request": request,
        "receipt": {
            "path": path.as_posix(),
            "sha256": f"sha256:{payload_sha256}",
            "size_bytes": path.stat().st_size,
            "media_type": "application/json",
        },
        "required_gaps": [],
        "next_action": (
            f"ethos lane repair-identity --receipt {path} "
            f"--receipt-sha256 sha256:{payload_sha256} --apply --authorize --json"
        ),
    }


def execute_identity_repair_suffix(
    *,
    root: Path,
    receipt_path: str,
    receipt_sha256: str,
    apply: bool,
    authorized: bool,
) -> dict[str, object]:
    """Revalidate and apply one exact suffix-repair receipt."""
    repo = repository_root(root)
    try:
        receipt = _load_identity_repair_receipt(repo, receipt_path, receipt_sha256)
        request = cast("dict[str, object]", receipt["request"])
        branch = str(request["branch"])
        refs = cast("dict[str, dict[str, str]]", request["refs"])
        commits = cast("list[dict[str, str]]", request["commits"])
        carried_proof = Attestation.model_validate(request["proof"])
    except (KeyError, OSError, TypeError, ValueError) as error:
        return _suffix_report("", "", "", [str(error) or "identity_repair_receipt_invalid"])
    status = workspace_status(repo, include_foreign_path_scope=False)
    lease = leases_by_branch(repo).get(branch, {})
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    old_head = str(request.get("head") or "")
    new_head = str(commits[-1].get("new_commit") or "") if commits else ""
    ref_state, ref_gaps = _suffix_ref_state(repo, refs)
    recovering = ref_state == "desired"
    live_generation = lease_generation(lease)
    expected_generation = cast("dict[str, object]", request.get("lease_generation") or {})
    carried_proof_facts, carried_proof_values = _carried_proof_facts(carried_proof)
    target_binding = _suffix_target_binding(repo, expected_generation, new_head)
    successor = {**expected_generation, **target_binding}
    successor.pop("payload_sha256", None)
    lease_is_successor = (
        recovering
        and set(successor) == set(live_generation) - {"payload_sha256"}
        and all(live_generation.get(key) == value for key, value in successor.items())
    )
    lease_current = live_generation == expected_generation or lease_is_successor
    live_proof = proof_attestation(repo, old_head) if not recovering else None
    gaps = [
        gap
        for valid, gap in (
            (status.get("branch") == branch, "identity_repair_branch_mismatch"),
            (status.get("role") == ROLE_WORK_LANE, "work_lane_required"),
            (not status.get("dirty") or recovering, "work_lane_dirty"),
            (authorized or not apply, "authorization_required"),
            (actor == str(request.get("actor") or ""), "identity_repair_actor_mismatch"),
            (lease.get("lease_state") == "valid", f"work_lane_lease_invalid:{branch}"),
            (lease_current, "identity_repair_lease_generation_stale"),
            (
                current_tracked_head(repo) == (new_head if recovering else old_head),
                "identity_repair_head_mismatch",
            ),
            (
                current_tree(repo, new_head if recovering else old_head) == request.get("tree"),
                "identity_repair_tree_mismatch",
            ),
            (
                carried_proof.predicate == "proof:execution"
                and carried_proof.subject == f"git:commit:{old_head}"
                and carried_proof.verdict == "pass"
                and carried_proof_facts.get("head") == old_head
                and carried_proof_facts.get("tree") == request.get("tree")
                and mutable_json(carried_proof_values.get("lease_generation"))
                == mutable_json(expected_generation)
                and (recovering or (live_proof is not None and live_proof.id == carried_proof.id)),
                "proof_not_proven",
            ),
        )
        if not valid
    ]
    gaps.extend(_validate_suffix_commits(repo, commits))
    gaps.extend(ref_gaps)
    gaps.extend(_suffix_worktree_gaps(repo, status, refs, recovering=recovering))
    if gaps or not apply:
        report = _suffix_report(branch, str(request.get("base_commit") or ""), old_head, gaps)
        report["state"] = "blocked" if gaps else "ready_to_repair_identity"
        report["request"] = request
        return report
    effect = GitEffect(
        updates={
            ref: GitRefUpdate(expected=update["expected"], desired=update["desired"])
            for ref, update in refs.items()
        }
    )
    authority = load_lease_bound_commitment(repo, lease=lease)
    plan = compile_observed_git_effect(
        repo,
        authority,
        effect,
        head=old_head,
        prior_attestations={"proof": carried_proof.model_dump(mode="json")},
        policy={"operation": "commit.identity-replace", "execution_branch": branch},
        values={
            "lease_generation": expected_generation,
            "lease_successor": successor,
            "identity_repair_receipt": receipt.get("digest"),
        },
    )

    def advance_lease() -> None:
        current = leases_by_branch(repo).get(branch, {})
        if (
            current.get("expected_head") == new_head
            and current.get("expected_tree") == target_binding["expected_tree"]
        ):
            return
        advance_lease_ref(
            state_database(repo),
            request=LeaseOperationRequest(
                operation="advance",
                branch=branch,
                holder_ref=actor,
                lease_id=str(lease.get("lease_id") or ""),
                expected_epoch=integer(lease.get("epoch")),
                expect_head=old_head,
                expected_expires_at=str(lease.get("expires_at") or ""),
                expected_payload_sha256=str(lease.get("payload_sha256") or ""),
                apply=True,
            ),
            binding=target_binding,
        )

    try:
        attestation = execute_git_effect(
            repo,
            plan,
            issuer=actor,
            projection=None if lease_is_successor else advance_lease,
        )
        synchronized = _sync_suffix_worktrees(repo, status, refs)
    except (OSError, TypeError, ValueError) as error:
        report = _suffix_report(
            branch,
            str(request.get("base_commit") or ""),
            old_head,
            ["identity_repair_cas_rejected"],
        )
        report["stderr"] = str(error)
        return report
    if any(item["worktree_sync"] == "failed" for item in synchronized):
        report = _suffix_report(
            branch,
            str(request.get("base_commit") or ""),
            old_head,
            ["identity_repair_worktree_sync_failed"],
        )
        report["worktree_sync"] = synchronized
        return report
    return {
        "verdict": "pass",
        "state": "identity_repaired",
        "branch": branch,
        "old_head": old_head,
        "new_head": new_head,
        "request": request,
        "effect": attestation.model_dump(mode="json"),
        "worktree_sync": synchronized,
        "required_gaps": [],
    }


def _carried_proof_facts(
    proof: Attestation,
) -> tuple[dict[str, object], dict[str, object]]:
    plan = cast("dict[str, object]", proof.payload.body.get("plan") or {})
    facts = cast("dict[str, object]", plan.get("facts") or {})
    return facts, cast("dict[str, object]", facts.get("values") or {})


def _suffix_target_binding(
    root: Path, generation: dict[str, object], new_head: str
) -> dict[str, str]:
    return {
        "expected_head": new_head,
        "expected_tree": current_tree(root, new_head),
        "base_commitment_path": str(generation.get("base_commitment_path") or ""),
        "base_commitment_bytes_sha256": str(generation.get("base_commitment_bytes_sha256") or ""),
        "base_commitment_digest": str(generation.get("base_commitment_digest") or ""),
    }


def _load_identity_repair_receipt(
    root: Path, receipt_path: str, receipt_sha256: str
) -> dict[str, object]:
    path = Path(receipt_path).resolve()
    store = _identity_repair_receipt_store(root).resolve()
    if not path.is_relative_to(store) or path.parent != store or path.suffix != ".json":
        message = "identity_repair_receipt_path_invalid"
        raise ValueError(message)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    expected = receipt_sha256.removeprefix("sha256:") or path.stem
    if digest != expected or path.stem != expected:
        message = "identity_repair_receipt_sha256_mismatch"
        raise ValueError(message)
    receipt = json.loads(raw)
    if not isinstance(receipt, dict):
        message = "identity_repair_receipt_invalid"
        raise TypeError(message)
    carried = str(receipt.get("digest") or "")
    unsigned = dict(receipt)
    unsigned.pop("digest", None)
    if carried != hashlib.sha256(_canonical_json(unsigned)).hexdigest():
        message = "identity_repair_receipt_digest_mismatch"
        raise ValueError(message)
    if receipt.get("kind") != "identity-repair-suffix-receipt":
        message = "identity_repair_receipt_invalid"
        raise ValueError(message)
    return receipt


def _validate_suffix_commits(root: Path, commits: list[dict[str, str]]) -> list[str]:
    gaps: list[str] = []
    previous_old = ""
    previous_new = ""
    for item in commits:
        old = str(item.get("old_commit") or "")
        new = str(item.get("new_commit") or "")
        metadata = commit_metadata(root, old) or {}
        old_raw = run_git(root, "cat-file", "commit", old, check=False, text=False)
        new_raw = run_git(root, "cat-file", "commit", new, check=False, text=False)
        old_message = old_raw.stdout.partition(b"\n\n")[2] if old_raw.returncode == 0 else b""
        new_message = new_raw.stdout.partition(b"\n\n")[2] if new_raw.returncode == 0 else b""
        checks = (
            (git_stdout(root, "rev-parse", f"{old}^") == item.get("old_parent"), "old_parent"),
            (git_stdout(root, "rev-parse", f"{new}^") == item.get("new_parent"), "new_parent"),
            (not previous_old or item.get("old_parent") == previous_old, "old_chain"),
            (not previous_new or item.get("new_parent") == previous_new, "new_chain"),
            (current_tree(root, old) == item.get("tree"), "old_tree"),
            (current_tree(root, new) == item.get("tree"), "new_tree"),
            (
                old_message == new_message
                and hashlib.sha256(old_message).hexdigest() == item.get("message_sha256"),
                "message",
            ),
            (
                all(
                    item.get(key.removeprefix("GIT_").lower()) == value
                    for key, value in metadata.items()
                ),
                "metadata",
            ),
            (verify_commit_trust(root, new).get("verdict") == "pass", "trust"),
        )
        gaps.extend(
            f"identity_repair_commit_{field}_drift:{old}" for valid, field in checks if not valid
        )
        previous_old = old
        previous_new = new
    return gaps


def _suffix_ref_state(root: Path, refs: dict[str, dict[str, str]]) -> tuple[str, list[str]]:
    observed = {ref: ref_head(root, ref) for ref in refs}
    if all(observed[ref] == update["expected"] for ref, update in refs.items()):
        return "expected", []
    if all(observed[ref] == update["desired"] for ref, update in refs.items()):
        return "desired", []
    return "mixed", [f"identity_repair_ref_stale:{ref}:{observed[ref]}" for ref in refs]


def _suffix_worktree_gaps(
    root: Path,
    status: dict[str, object],
    refs: dict[str, dict[str, str]],
    *,
    recovering: bool,
) -> list[str]:
    worktrees = cast("list[dict[str, object]]", status.get("worktrees") or [])
    gaps: list[str] = []
    for ref, update in refs.items():
        branch = ref.removeprefix("refs/heads/")
        paths = ref_worktree_paths(worktrees, branch)
        terminal = (
            worktree_sync_gap(
                root,
                paths,
                branch,
                update["desired"],
                update["desired"],
                update["desired"],
            )
            if recovering
            else ""
        )
        gap = (
            ""
            if recovering and not terminal
            else worktree_sync_gap(
                root,
                paths,
                branch,
                update["desired"] if recovering else update["expected"],
                update["expected"],
                update["desired"],
            )
        )
        if gap:
            gaps.append(f"identity_repair_{branch.replace('/', '_')}_{gap}")
    return gaps


def _sync_suffix_worktrees(
    root: Path, status: dict[str, object], refs: dict[str, dict[str, str]]
) -> list[dict[str, object]]:
    worktrees = cast("list[dict[str, object]]", status.get("worktrees") or [])
    return [
        {
            "branch": ref.removeprefix("refs/heads/"),
            **sync_ref_worktrees(
                root,
                ref_worktree_paths(worktrees, ref.removeprefix("refs/heads/")),
                ref.removeprefix("refs/heads/"),
                update["desired"],
                update["expected"],
            ),
        }
        for ref, update in refs.items()
    ]


def _linear_suffix(root: Path, base: str, head: str) -> list[str]:
    if not base or not head:
        message = "identity_repair_suffix_coordinate_missing"
        raise ValueError(message)
    contained = run_git(root, "merge-base", "--is-ancestor", base, head, check=False)
    if contained.returncode:
        message = "identity_repair_base_not_ancestor"
        raise ValueError(message)
    commits = git_stdout(root, "rev-list", "--reverse", f"{base}..{head}").splitlines()
    if not commits:
        message = "identity_repair_suffix_empty"
        raise ValueError(message)
    previous = base
    for commit in commits:
        parents = git_stdout(root, "rev-list", "--parents", "-n", "1", commit).split()
        if parents != [commit, previous]:
            message = f"identity_repair_suffix_not_linear:{commit}"
            raise ValueError(message)
        previous = commit
    return commits


def _suffix_train_refs(
    root: Path, branch: str, mapping: dict[str, str]
) -> tuple[dict[str, str], list[str]]:
    policy = load_branch_role_policy(root)
    branches = [policy.candidate_branch, policy.accepted_branch, policy.release_branch, branch]
    refs = {f"refs/heads/{name}": ref_head(root, name) for name in dict.fromkeys(branches)}
    suffix = set(mapping) | set(mapping.values())
    gaps = [
        f"identity_repair_ref_outside_suffix:{ref}:{head}"
        for ref, head in refs.items()
        if head not in suffix
    ]
    return {ref: head for ref, head in refs.items() if head in mapping}, gaps


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _identity_repair_receipt_store(root: Path) -> Path:
    return Path(git_common_dir(root)) / "ethos" / "requests" / "identity-repair"


def _suffix_report(branch: str, base: str, head: str, gaps: list[str]) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "blocked",
        "branch": branch,
        "base_commit": base,
        "head": head,
        "request": {},
        "receipt": {},
        "required_gaps": list(dict.fromkeys(gaps)),
        "next_action": "",
    }
