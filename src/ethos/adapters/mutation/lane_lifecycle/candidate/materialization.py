"""Fresh admission of a retained candidate index and worktree projection."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_report
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.repo.trust_anchor.verification import verify_commit_trust
from ethos.adapters.repo.worktree_effects import hold_worktree_refs
from ethos.adapters.repo.worktree_effects import sync_worktree
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.semantic import canonical_json_digest


def _fail(message: str) -> None:
    raise ValueError(message)


def _materialization_facts(
    repo: Path, policy: BranchRolePolicy, preserved_preimage: str, retention_ref: str, reason: str
) -> tuple[dict[str, str], list[str]]:
    status = workspace_status(repo)
    candidate = cast("dict[str, object]", status["candidate"])
    head = str(candidate.get("head") or "")
    path = str(candidate.get("worktree_path") or "")
    retained = ref_head(repo, retention_ref) if retention_ref.startswith("refs/") else ""
    facts = {
        "repository": git_common_dir(repo),
        "path": path,
        "head": head,
        "accepted_head": ref_head(repo, f"refs/heads/{policy.accepted_branch}"),
        "retention_head": retained,
        "preserved_preimage": preserved_preimage,
        "retention_ref": retention_ref,
        "reason": reason.strip(),
        "actor": os.environ.get("ETHOS_ACTOR", "").strip(),
    }
    gaps = [
        gap
        for gap, present in (
            ("accepted_root_required", status["role"] != ROLE_ACCEPTED_ROOT),
            ("accepted_root_dirty", bool(status["dirty"])),
            ("candidate_worktree_missing", not candidate.get("worktree_exists")),
            ("candidate_preserved_preimage_required", not preserved_preimage),
            ("candidate_retention_ref_required", not retained),
            ("candidate_materialization_reason_required", not reason.strip()),
            ("git_effect_issuer_invalid", not facts["actor"]),
        )
        if present
    ]
    if gaps:
        return facts, gaps
    resolved = run_git(repo, "rev-parse", "--verify", preserved_preimage + "^{commit}", check=False)
    if resolved.returncode or resolved.stdout.strip() != preserved_preimage:
        return facts, ["candidate_preserved_preimage_invalid"]
    if not is_ancestor(repo, preserved_preimage, retained):
        return facts, ["candidate_preserved_preimage_not_retained"]
    if not is_ancestor(repo, preserved_preimage, head):
        return facts, ["candidate_preserved_preimage_not_ancestor"]
    trust = verify_commit_trust(repo, (preserved_preimage, head))
    if trust["required_gaps"]:
        return facts, cast("list[str]", trust["required_gaps"])
    gap = worktree_sync_gap(
        repo, (Path(path),), policy.candidate_branch, head, preserved_preimage, head
    )
    if gap and worktree_sync_gap(repo, (Path(path),), policy.candidate_branch, head, head, head):
        gaps.append(gap)
    return facts, gaps


def materialize_candidate(
    *,
    root: Path,
    preserved_preimage: str,
    retention_ref: str,
    reason: str,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
    expect_state: str | None = None,
) -> dict[str, object]:
    """Freshly admit one retained candidate projection; never replay or move a ref."""
    repo = repository_root(root)
    policy = load_branch_role_policy(repo)
    facts, gaps = _materialization_facts(repo, policy, preserved_preimage, retention_ref, reason)
    head = facts["head"]
    action = f"ethos status --root {shlex.quote(repo.as_posix())} --json"
    if gaps:
        return lifecycle_report(policy.candidate_branch, head, "blocked", gaps, next_action=action)
    token = canonical_json_digest(facts)
    command = shlex.join(
        (
            "ethos",
            "lane",
            "candidate",
            "--materialize",
            "--preserved-preimage",
            preserved_preimage,
            "--retention-ref",
            retention_ref,
            "--reason",
            reason,
            "--expect-head",
            head,
            "--expect-state",
            token,
            "--apply",
            "--authorize",
            "--root",
            str(repo),
            "--json",
        )
    )
    if not apply:
        return lifecycle_report(
            policy.candidate_branch,
            head,
            "ready_to_materialize",
            [],
            path=facts["path"],
            state_digest=token,
            observation=facts,
            next_action=command,
            user_decision_required=True,
        )
    gaps = [
        gap
        for gap, present in (
            ("authorization_required", not authorized),
            ("expect_head_required", not expect_head),
            ("expect_head_mismatch", bool(expect_head) and expect_head != head),
            ("candidate_materialization_exact_request_required", not expect_state),
            ("candidate_materialization_state_stale", bool(expect_state) and expect_state != token),
        )
        if present
    ]
    if gaps:
        return lifecycle_report(policy.candidate_branch, head, "blocked", gaps, next_action=action)
    assertions = {
        f"refs/heads/{policy.candidate_branch}": head,
        f"refs/heads/{policy.accepted_branch}": facts["accepted_head"],
        retention_ref: facts["retention_head"],
    }
    try:
        with hold_worktree_refs(repo, assertions):
            current, gaps = _materialization_facts(
                repo, policy, preserved_preimage, retention_ref, reason
            )
            if gaps or current != facts:
                _fail(gaps[0] if gaps else "candidate_materialization_state_stale")
            result = sync_worktree(
                repo,
                Path(facts["path"]),
                branch=policy.candidate_branch,
                previous=preserved_preimage,
                head=head,
            )
    except (OSError, ValueError) as error:
        return lifecycle_report(
            policy.candidate_branch, head, "blocked", [str(error)], next_action=action
        )
    return lifecycle_report(
        policy.candidate_branch,
        head,
        "materialized",
        [],
        path=facts["path"],
        effect_state=result.payload.body["result"]["state"],
        attestation=result.model_dump(mode="json"),
        next_action="ethos land --json",
    )
