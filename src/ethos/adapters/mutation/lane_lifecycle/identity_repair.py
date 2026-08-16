"""Same-tree commit identity replacement across the local integration train."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
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
from ethos.adapters.repo.git_effects import create_git_commit
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_ref_worktrees import ref_worktree_paths
from ethos.adapters.repo.git_ref_worktrees import sync_ref_worktrees
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.lease.lifecycle.transitions import advance_lease_ref
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from ethos.contracts.semantic import Commitment


@dataclass(frozen=True, slots=True)
class _Replacement:
    root: Path
    branch: str
    status: dict[str, object]
    refs: dict[str, str]
    authority: Commitment
    evidence: dict[str, object]
    lease: dict[str, object]
    old: str
    new: str


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
    commits, range_gaps = _linear_suffix(repo, base_commit, head)
    gaps.extend(range_gaps)
    train, train_gaps = _suffix_train_refs(repo, branch, commits)
    gaps.extend(train_gaps)
    if gaps:
        return _suffix_report(branch, base_commit, head, gaps)
    if proof is None:
        return _suffix_report(branch, base_commit, head, ["proof_not_proven"])
    try:
        replacements = _create_signed_suffix(repo, base_commit, commits)
    except ValueError as error:
        return _suffix_report(branch, base_commit, head, [str(error)])
    mapping = {str(item["old_commit"]): str(item["new_commit"]) for item in replacements}
    refs = {
        ref: {"expected": old, "desired": mapping[old]}
        for ref, old in train.items()
    }
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
    gaps.extend(_validate_suffix_commits(repo, request, commits))
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
                expected_epoch=int(lease.get("epoch") or 0),
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
        "base_commitment_bytes_sha256": str(
            generation.get("base_commitment_bytes_sha256") or ""
        ),
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


def _validate_suffix_commits(
    root: Path, request: dict[str, object], commits: list[dict[str, str]]
) -> list[str]:
    gaps: list[str] = []
    expected_old_parent = str(request.get("base_commit") or "")
    expected_new_parent = expected_old_parent
    for item in commits:
        old = str(item.get("old_commit") or "")
        new = str(item.get("new_commit") or "")
        metadata = _commit_metadata(root, old)
        old_raw = run_git(root, "cat-file", "commit", old, check=False, text=False)
        new_raw = run_git(root, "cat-file", "commit", new, check=False, text=False)
        old_message = old_raw.stdout.partition(b"\n\n")[2] if old_raw.returncode == 0 else b""
        new_message = new_raw.stdout.partition(b"\n\n")[2] if new_raw.returncode == 0 else b""
        checks = (
            (git_stdout(root, "rev-parse", f"{old}^") == expected_old_parent, "old_parent"),
            (git_stdout(root, "rev-parse", f"{new}^") == expected_new_parent, "new_parent"),
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
            f"identity_repair_commit_{field}_drift:{old}"
            for valid, field in checks
            if not valid
        )
        expected_old_parent = old
        expected_new_parent = new
    return gaps


def _suffix_ref_state(
    root: Path, refs: dict[str, dict[str, str]]
) -> tuple[str, list[str]]:
    observed = {ref: ref_head(root, ref) for ref in refs}
    if all(observed[ref] == update["expected"] for ref, update in refs.items()):
        return "expected", []
    if all(observed[ref] == update["desired"] for ref, update in refs.items()):
        return "desired", []
    return "mixed", [
        f"identity_repair_ref_stale:{ref}:{observed[ref]}"
        for ref in refs
    ]


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
        gap = "" if recovering and not terminal else worktree_sync_gap(
            root,
            paths,
            branch,
            update["desired"] if recovering else update["expected"],
            update["expected"],
            update["desired"],
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


def _linear_suffix(root: Path, base: str, head: str) -> tuple[list[str], list[str]]:
    if not base or not head:
        return [], ["identity_repair_suffix_coordinate_missing"]
    contained = run_git(root, "merge-base", "--is-ancestor", base, head, check=False)
    if contained.returncode:
        return [], ["identity_repair_base_not_ancestor"]
    commits = git_stdout(root, "rev-list", "--reverse", f"{base}..{head}").splitlines()
    if not commits:
        return [], ["identity_repair_suffix_empty"]
    previous = base
    for commit in commits:
        parents = git_stdout(root, "rev-list", "--parents", "-n", "1", commit).split()
        if parents != [commit, previous]:
            return commits, [f"identity_repair_suffix_not_linear:{commit}"]
        previous = commit
    return commits, []


def _suffix_train_refs(
    root: Path, branch: str, commits: list[str]
) -> tuple[dict[str, str], list[str]]:
    policy = load_branch_role_policy(root)
    branches = [policy.candidate_branch, policy.accepted_branch, policy.release_branch, branch]
    refs = {f"refs/heads/{name}": ref_head(root, name) for name in dict.fromkeys(branches)}
    suffix = set(commits)
    gaps = [
        f"identity_repair_ref_outside_suffix:{ref}:{head}"
        for ref, head in refs.items()
        if head not in suffix
    ]
    return refs, gaps


def _create_signed_suffix(root: Path, base: str, commits: list[str]) -> list[dict[str, str]]:
    replacements: list[dict[str, str]] = []
    new_parent = base
    for old in commits:
        metadata = _commit_metadata(root, old)
        raw = run_git(root, "cat-file", "commit", old, check=False, text=False)
        message = raw.stdout.partition(b"\n\n")[2] if raw.returncode == 0 else b""
        if not metadata or not message:
            error = f"identity_repair_commit_metadata_unreadable:{old}"
            raise ValueError(error)
        tree = current_tree(root, old)
        completed = create_git_commit(
            root,
            tree=tree,
            parent=new_parent,
            message=message.decode("utf-8", errors="surrogateescape"),
            preserve_message=True,
            environment=metadata,
        )
        if completed.returncode or not completed.stdout.strip():
            gap = completed.stderr.strip() or "identity_repair_commit_creation_failed"
            error = f"{gap}:{old}"
            raise ValueError(error)
        new = completed.stdout.strip()
        if new == old:
            error = f"identity_repair_commit_identity_unchanged:{old}"
            raise ValueError(error)
        replacements.append(
            {
                "old_commit": old,
                "new_commit": new,
                "old_parent": git_stdout(root, "rev-parse", f"{old}^"),
                "new_parent": new_parent,
                "tree": tree,
                "message_sha256": hashlib.sha256(message).hexdigest(),
                **{key.removeprefix("GIT_").lower(): value for key, value in metadata.items()},
            }
        )
        new_parent = new
    return replacements


def _commit_metadata(root: Path, commit: str) -> dict[str, str]:
    completed = run_git(
        root,
        "show",
        "-s",
        "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI",
        commit,
        check=False,
    )
    if completed.returncode:
        return {}
    fields = completed.stdout.rstrip("\n").split("\0")
    if len(fields) != 6:
        return {}
    author, author_email, authored_at, committer, committer_email, committed_at = fields
    return {
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_AUTHOR_DATE": authored_at,
        "GIT_COMMITTER_NAME": committer,
        "GIT_COMMITTER_EMAIL": committer_email,
        "GIT_COMMITTER_DATE": committed_at,
    }


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


def repair_commit_identity(
    *,
    root: Path,
    old_commit: str,
    new_commit: str,
    expect_head: str,
    apply: bool,
    authorized: bool,
) -> dict[str, object]:
    """Replace one semantically identical commit OID through exact train-wide CAS."""
    status = workspace_status(root, include_foreign_path_scope=False)
    branch = str(status.get("branch") or "")
    head = current_tracked_head(root)
    lease = leases_by_branch(root).get(branch, {})
    proof = proof_attestation(root, new_commit)
    trust = verify_commit_trust(root, new_commit)
    train, update_gaps = _train_refs(root, old_commit, new_commit)
    gaps = [
        gap
        for valid, gap in (
            (status.get("role") == ROLE_WORK_LANE, "work_lane_required"),
            (not status.get("dirty"), "work_lane_dirty"),
            (authorized or not apply, "authorization_required"),
            (expect_head == new_commit, "expect_head_mismatch"),
            (head == new_commit, "identity_repair_head_mismatch"),
            (old_commit != new_commit, "identity_repair_oid_unchanged"),
            (
                equivalent_commit_identity(root, old_commit, new_commit),
                "identity_repair_commit_payload_mismatch",
            ),
            (lease.get("lease_state") == "valid", f"work_lane_lease_invalid:{branch}"),
            (
                str(lease.get("holder_ref") or "") == os.environ.get("ETHOS_ACTOR", "").strip(),
                "lease_actor_mismatch",
            ),
            (str(lease.get("expected_head") or "") == new_commit, "lease_head_stale"),
            (
                str(lease.get("expected_tree") or "") == current_tree(root, new_commit),
                "lease_expected_tree_stale",
            ),
            (proof is not None, (proof_gaps(root, new_commit) or ["proof_not_proven"])[0]),
        )
        if not valid
    ]
    trust_gaps = trust.get("required_gaps")
    if isinstance(trust_gaps, list):
        gaps.extend(str(gap) for gap in trust_gaps)
    gaps.extend(update_gaps)
    gaps.extend(_worktree_gaps(root, status, train, old_commit, new_commit))
    report = _report(branch, old_commit, new_commit, trust, gaps)
    if gaps or not apply:
        return report | {"state": "blocked" if gaps else "ready_to_repair_identity"}
    authority = load_lease_bound_commitment(root, lease=lease)
    evidence = {
        "proof": proof.model_dump(mode="json") if proof is not None else {},
        "commit_trust": trust,
    }
    replacement = _Replacement(
        root=root,
        branch=branch,
        status=status,
        refs=train,
        authority=authority,
        evidence=evidence,
        lease=lease,
        old=old_commit,
        new=new_commit,
    )
    try:
        candidate_attestation = _apply_candidate_replacement(replacement)
        accepted_attestation = _apply_accepted_replacement(replacement)
    except ValueError as error:
        return _report(
            branch,
            old_commit,
            new_commit,
            trust,
            ["identity_repair_cas_rejected"],
            stderr=str(error),
        )
    return _report(
        branch,
        old_commit,
        new_commit,
        trust,
        [],
        state="identity_repaired",
        candidate_attestation=candidate_attestation,
        accepted_attestation=accepted_attestation,
    )


def _train_refs(root: Path, old: str, new: str) -> tuple[dict[str, str], list[str]]:
    policy = load_branch_role_policy(root)
    branches = [policy.candidate_branch, policy.accepted_branch]
    if policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF:
        branches.append(policy.release_branch)
    heads = {branch: ref_head(root, branch) for branch in branches}
    gaps = [
        f"identity_repair_ref_stale:{branch}:{head}"
        for branch, head in heads.items()
        if head not in {old, new}
    ]
    return heads, gaps


def _worktree_gaps(
    root: Path,
    status: dict[str, object],
    refs: dict[str, str],
    old: str,
    new: str,
) -> list[str]:
    worktrees = cast("list[dict[str, object]]", status.get("worktrees") or [])
    gaps = []
    for branch, head in refs.items():
        if head != old:
            continue
        paths = ref_worktree_paths(worktrees, branch)
        if gap := worktree_sync_gap(root, paths, branch, old, old, new):
            gaps.append(f"identity_repair_{branch.replace('/', '_')}_{gap}")
    return gaps


def _sync_branch_worktrees(
    root: Path,
    status: dict[str, object],
    branch: str,
    old: str,
    new: str,
) -> dict[str, object]:
    worktrees = cast("list[dict[str, object]]", status.get("worktrees") or [])
    return sync_ref_worktrees(
        root,
        ref_worktree_paths(worktrees, branch),
        branch,
        new,
        old,
    )


def _apply_candidate_replacement(replacement: _Replacement) -> dict[str, object]:
    root, old, new = replacement.root, replacement.old, replacement.new
    policy = load_branch_role_policy(root)
    candidate = policy.candidate_branch
    if replacement.refs[candidate] == new:
        sync = _sync_branch_worktrees(root, replacement.status, candidate, old, new)
        if sync["worktree_sync"] == "failed":
            message = "identity_repair_candidate_worktree_sync_failed"
            raise ValueError(message)
        return {"state": "recognized", "worktree_sync": sync}
    effect = GitEffect(
        updates={f"refs/heads/{candidate}": GitRefUpdate(expected=old, desired=new)},
        assertions={f"refs/heads/{replacement.branch}": new},
    )
    plan = _plan(replacement, effect)
    attestation = execute_git_effect(root, plan, issuer=str(replacement.lease["holder_ref"]))
    sync = _sync_branch_worktrees(root, replacement.status, candidate, old, new)
    if sync["worktree_sync"] == "failed":
        message = "identity_repair_candidate_worktree_sync_failed"
        raise ValueError(message)
    return {"effect": attestation.model_dump(mode="json"), "worktree_sync": sync}


def _apply_accepted_replacement(replacement: _Replacement) -> dict[str, object]:
    root, old, new = replacement.root, replacement.old, replacement.new
    policy = load_branch_role_policy(root)
    branches = [policy.accepted_branch]
    if (
        policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
        and replacement.refs[policy.release_branch] == old
    ):
        branches.append(policy.release_branch)
    updates = {
        f"refs/heads/{name}": GitRefUpdate(expected=old, desired=new)
        for name in branches
        if replacement.refs[name] == old
    }
    if not updates:
        synchronized = [
            {"branch": name, **_sync_branch_worktrees(root, replacement.status, name, old, new)}
            for name in branches
        ]
        if any(item["worktree_sync"] == "failed" for item in synchronized):
            message = "identity_repair_accepted_worktree_sync_failed"
            raise ValueError(message)
        return {"state": "recognized", "worktree_sync": synchronized}
    effect = GitEffect(
        updates=updates,
        assertions={f"refs/heads/{policy.candidate_branch}": new},
    )
    plan = _plan(replacement, effect)
    attestation = execute_git_effect(root, plan, issuer=str(replacement.lease["holder_ref"]))
    synchronized = [
        {"branch": name, **_sync_branch_worktrees(root, replacement.status, name, old, new)}
        for name in branches
        if replacement.refs[name] == old
    ]
    if any(item["worktree_sync"] == "failed" for item in synchronized):
        message = "identity_repair_accepted_worktree_sync_failed"
        raise ValueError(message)
    return {"effect": attestation.model_dump(mode="json"), "worktree_sync": synchronized}


def _plan(replacement: _Replacement, effect: GitEffect):
    return compile_observed_git_effect(
        replacement.root,
        replacement.authority,
        effect,
        head=replacement.new,
        prior_attestations=replacement.evidence,
        policy={
            "operation": "commit.identity-replace",
            "execution_branch": replacement.branch,
        },
        values={
            "lease_generation": lease_generation(replacement.lease),
            "old_commit": replacement.old,
            "new_commit": replacement.new,
        },
    )


def _report(
    branch: str,
    old: str,
    new: str,
    trust: dict[str, object],
    gaps: list[str],
    **details: object,
) -> dict[str, object]:
    return {
        "verdict": "block" if gaps else "pass",
        "state": "blocked" if gaps else "ready_to_repair_identity",
        "branch": branch,
        "old_commit": old,
        "new_commit": new,
        "trust": trust,
        "required_gaps": list(dict.fromkeys(gaps)),
        **details,
    }
