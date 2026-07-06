from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ethos.adapters.mutation.proof import carry_executed_proof_record
from ethos.adapters.mutation.proof import executed_proof_record
from ethos.adapters.repo.status import workspace_status
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.contracts.branch_roles import load_branch_role_policy


def _proof_gaps(root: Path, current_head: str) -> list[str]:
    """Blocking gaps when no executed proof is bound to the exact current HEAD.

    Binds the mutation to executed proof: a land/publish cannot proceed unless
    `ethos prove --execute` recorded a proof at this HEAD. This is the runtime
    precondition that turns "only proven evidence may satisfy land/publish" from
    prose into an enforced barrier (tao First Principle #2 / #3).
    """
    record = executed_proof_record(root, current_head)
    if record is None:
        return ["proof_not_proven"]
    return []


def _candidate_proof_gaps(candidate_path: Path, candidate_head: str) -> list[str]:
    """Blocking gaps when closeout lacks proof for the head being promoted."""
    return _proof_gaps(candidate_path, candidate_head)


def _closeout_candidate_gaps(
    root: Path,
    candidate: dict[str, object],
    current_head: str,
    *,
    require_proof: bool = True,
) -> list[str]:
    """Candidate-side closeout blockers, ordered by lifecycle before evidence."""
    if not candidate["exists"]:
        return ["candidate_branch_missing"]
    if not candidate["worktree_exists"]:
        return ["candidate_worktree_missing"]
    candidate_path = Path(str(candidate["worktree_path"]))
    if workspace_status(candidate_path)["dirty"]:
        return ["candidate_worktree_dirty"]
    candidate_head = str(candidate.get("head") or "")
    if not _is_ancestor(root, current_head, candidate_head):
        return ["candidate_diverged_from_accepted"]
    if not require_proof:
        return []
    return _candidate_proof_gaps(candidate_path, candidate_head)


@dataclass(frozen=True)
class MutationRequest:
    command: str
    apply: bool
    authorized: bool
    expect_head: str | None


@dataclass(frozen=True)
class MutationDecision:
    ok: bool
    state: str
    gaps: tuple[str, ...] = ()


def remediation_for_gaps(gaps: tuple[str, ...] | list[str]) -> list[dict[str, object]]:
    """Machine-readable repair hints for common mutation blockers."""
    hints: list[dict[str, object]] = []
    gap_set = tuple(str(gap) for gap in gaps)
    for gap in gap_set:
        if gap in {"work_lane_dirty", "accepted_root_dirty", "candidate_worktree_dirty"}:
            hints.append(
                {
                    "gap": gap,
                    "kind": "dirty_state",
                    "next_actions": [
                        "inspect dirty_provenance in ethos status --json",
                        "commit intentional changes or back up and reset generated residue",
                    ],
                }
            )
        elif gap == "candidate_base_stale":
            hints.append(
                {
                    "gap": gap,
                    "kind": "stale_base",
                    "next_actions": [
                        "ethos lane refresh-base --apply --authorize --expect-head <head> --json",
                        "rerun proof after the lane is replayed onto candidate/dev",
                    ],
                }
            )
        elif gap == "accepted_advanced_concurrently":
            hints.append(
                {
                    "gap": gap,
                    "kind": "accepted_advanced_concurrently",
                    "next_actions": [
                        "a concurrent landing advanced accepted after this proof was bound",
                        "re-read the accepted head and rebase candidate onto it",
                        "rerun ethos land --closeout --expect-head <new-head> after re-proving",
                    ],
                }
            )
        elif gap.startswith("coordination_gap:scope_overlap:"):
            branch = gap.rsplit(":", 1)[-1]
            hints.append(
                {
                    "gap": gap,
                    "kind": "lane_overlap",
                    "next_actions": [
                        "do not land a temporary overlapping lane directly",
                        (
                            "move or replay the verified head through "
                            f"the legitimate leased lane {branch}"
                        ),
                        "remove the temporary lane after the legitimate lane is current",
                    ],
                }
            )
    return hints


def evaluate_mutation(
    request: MutationRequest,
    *,
    root: Path,
    current_head: str,
) -> MutationDecision:
    gaps: list[str] = []
    if request.apply and not request.authorized:
        gaps.append("authorization_required")
    if request.apply and request.expect_head is None:
        gaps.append("expect_head_required")
    elif request.expect_head is not None and request.expect_head != current_head:
        gaps.append("expect_head_mismatch")
    status = workspace_status(root)
    if status["role"] != ROLE_WORK_LANE:
        gaps.append("protected_root_mutation")
    elif status["dirty"]:
        gaps.append("work_lane_dirty")
    else:
        closeout = cast("dict[str, object]", status.get("closeout_support", {}))
        gaps.extend(str(gap) for gap in cast("list[object]", closeout.get("required_gaps", [])))
    if request.apply:
        gaps.extend(_proof_gaps(root, current_head))
    if gaps:
        return MutationDecision(ok=False, state="blocked", gaps=tuple(gaps))
    if not request.apply:
        return MutationDecision(ok=True, state="dry_run")
    return MutationDecision(ok=True, state=f"{request.command}_ready")


def evaluate_closeout_mutation(
    request: MutationRequest,
    *,
    root: Path,
    current_head: str,
) -> MutationDecision:
    gaps: list[str] = []
    if request.apply and not request.authorized:
        gaps.append("authorization_required")
    if request.expect_head is None:
        if request.apply:
            gaps.append("expect_head_required")
    elif request.expect_head != current_head:
        gaps.append("expect_head_mismatch")
    status = workspace_status(root)
    if status["role"] != ROLE_ACCEPTED_ROOT:
        gaps.append("accepted_root_required")
    elif status["dirty"]:
        gaps.append("accepted_root_dirty")
    candidate = cast("dict[str, object]", status["candidate"])
    gaps.extend(
        _closeout_candidate_gaps(root, candidate, current_head, require_proof=request.apply)
    )
    if gaps:
        return MutationDecision(ok=False, state="blocked", gaps=tuple(gaps))
    if not request.apply:
        return MutationDecision(ok=True, state="dry_run")
    return MutationDecision(ok=True, state=f"{request.command}_ready")


def apply_land_to_candidate(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
    admitted_decision: MutationDecision | None = None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    decision = admitted_decision or evaluate_mutation(
        MutationRequest(
            command="land",
            apply=True,
            authorized=authorized,
            expect_head=expect_head,
        ),
        root=root,
        current_head=current_head,
    )
    if not decision.ok:
        return {
            "ok": False,
            "state": decision.state,
            "branch": policy.candidate_branch,
            "head": current_head,
            "required_gaps": list(decision.gaps),
            "remediation": remediation_for_gaps(decision.gaps),
        }
    base_report = candidate_base_report(root=root)
    if not base_report["ok"]:
        return base_report
    candidate_path = Path(str(base_report["path"]))
    completed = _git(candidate_path, "merge", "--ff-only", current_head, check=False)
    if completed.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": candidate_path.as_posix(),
            "required_gaps": ["candidate_update_failed"],
            "remediation": remediation_for_gaps(["candidate_update_failed"]),
            "stderr": completed.stderr.strip(),
        }
    proof_carry = carry_executed_proof_record(
        source_root=root, target_root=candidate_path, head=current_head
    )
    return {
        "ok": True,
        "state": "candidate_validated",
        "branch": policy.candidate_branch,
        "head": current_head,
        "path": candidate_path.as_posix(),
        "proof_carry": proof_carry,
        "required_gaps": [],
    }


def apply_candidate_to_accepted(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    decision = evaluate_closeout_mutation(
        MutationRequest(
            command="closeout",
            apply=True,
            authorized=authorized,
            expect_head=expect_head,
        ),
        root=root,
        current_head=current_head,
    )
    if not decision.ok:
        return {
            "ok": False,
            "state": decision.state,
            "branch": policy.accepted_branch,
            "source_branch": policy.candidate_branch,
            "head": current_head,
            "previous_head": current_head,
            "required_gaps": list(decision.gaps),
            "remediation": remediation_for_gaps(decision.gaps),
        }
    status = workspace_status(root)
    candidate_head = str(cast("dict[str, object]", status["candidate"])["head"])
    if not _is_ancestor(root, current_head, candidate_head):
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.accepted_branch,
            "source_branch": policy.candidate_branch,
            "head": current_head,
            "candidate_head": candidate_head,
            "previous_head": current_head,
            "required_gaps": ["candidate_diverged_from_accepted"],
        }
    # Atomic compare-and-swap: advance the accepted ref to candidate_head ONLY IF the
    # accepted ref is still exactly what it was when the proof was bound. git's
    # update-ref <ref> <newvalue> <oldvalue> is the native CAS primitive. The oldvalue
    # must be the accepted REF's own resolved value (not HEAD, which need not coincide
    # with refs/heads/<accepted> in every root) so the swap compares like-with-like: a
    # concurrent agent that advanced the accepted ref after we read it makes the oldvalue
    # mismatch, so the swap fails cleanly rather than overwriting their landing (Axiom 1
    # held: the proof always covers exactly the tree that becomes accepted; the
    # check-time / use-time TOCTOU window is eliminated).
    accepted_ref = f"refs/heads/{policy.accepted_branch}"
    accepted_old = _git(root, "rev-parse", "--verify", accepted_ref).stdout.strip()
    completed = _git(
        root,
        "update-ref",
        accepted_ref,
        candidate_head,
        accepted_old,
        check=False,
        env={"ETHOS_ALLOW_REF_MOVE": "1"},
    )
    if completed.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.accepted_branch,
            "source_branch": policy.candidate_branch,
            "head": current_head,
            "previous_head": current_head,
            "required_gaps": ["accepted_advanced_concurrently"],
            "remediation": remediation_for_gaps(["accepted_advanced_concurrently"]),
            "stderr": completed.stderr.strip(),
        }
    # CAS won: sync the accepted worktree to the ref it now points at. This is a
    # fast-forward (candidate_head descends from current_head, checked above), so
    # --keep advances the tree without discarding any tracked local state.
    _git(
        root,
        "reset",
        "--keep",
        candidate_head,
        check=False,
        env={"ETHOS_ALLOW_REF_MOVE": "1"},
    )
    return {
        "ok": True,
        "state": "accepted_validated",
        "branch": policy.accepted_branch,
        "source_branch": policy.candidate_branch,
        "head": candidate_head,
        "previous_head": current_head,
        "required_gaps": [],
    }


def candidate_base_report(*, root: Path) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    status = workspace_status(root)
    if not cast("dict[str, object]", status["candidate"])["exists"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "required_gaps": ["candidate_branch_missing"],
        }
    if not cast("dict[str, object]", status["candidate"])["worktree_exists"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "required_gaps": ["candidate_worktree_missing"],
        }
    candidate_path = Path(str(cast("dict[str, object]", status["candidate"])["worktree_path"]))
    candidate_status = workspace_status(candidate_path)
    if candidate_status["dirty"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": candidate_path.as_posix(),
            "required_gaps": ["candidate_worktree_dirty"],
        }
    candidate_head = str(cast("dict[str, object]", status["candidate"])["head"])
    if not _is_ancestor(root, candidate_head, current_head):
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "candidate_head": candidate_head,
            "path": candidate_path.as_posix(),
            "required_gaps": ["candidate_base_stale"],
            "remediation": remediation_for_gaps(["candidate_base_stale"]),
        }
    return {
        "ok": True,
        "state": "candidate_base_current",
        "branch": policy.candidate_branch,
        "head": current_head,
        "candidate_head": candidate_head,
        "path": candidate_path.as_posix(),
        "required_gaps": [],
    }


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = _git(root, "merge-base", "--is-ancestor", ancestor, descendant, check=False)
    return completed.returncode == 0


def _git(
    root: Path,
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = {**os.environ, **env} if env is not None else None
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
        env=run_env,
    )
