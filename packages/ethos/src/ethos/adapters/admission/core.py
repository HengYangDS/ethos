from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.closeout_intent.core import MarkerExpectation
from ethos.adapters.admission.closeout_intent.core import consume_closeout_intent
from ethos.adapters.admission.identity import push_identity_policy_report
from ethos.adapters.admission.prewrite import has_invalid_path_token_character
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.admission.shell import command_risk
from ethos.adapters.admission.shell import git_stash_policy
from ethos.adapters.mutation.proof import executed_proof_record
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.core import advance_lease_head
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.repository.policy.gates import gate_policy_digest
from ethos_core.contracts.branch.roles import PROTECTED_WRITE_ROLES

if TYPE_CHECKING:
    from ethos_core.contracts.branch.roles import BranchRolePolicy

HOOK_LAYERS = {
    "context": {
        "timing": "before_target_resolution",
        "duty": "refresh_repository_truth",
        "fallback": False,
    },
    "pre-tool": {
        "timing": "before_write_capable_tool",
        "duty": "block_unadmitted_tracked_writes",
        "fallback": False,
    },
    "pre-run": {
        "timing": "before_shell_command",
        "duty": "classify_mutation_risk",
        "fallback": False,
    },
    "post-write": {
        "timing": "after_write",
        "duty": "fuse_on_unexpected_mutation",
        "fallback": False,
    },
    "git": {
        "timing": "commit_or_push",
        "duty": "deterministic_local_fallback",
        "fallback": True,
    },
    "ci": {
        "timing": "hosted_pipeline",
        "duty": "integration_and_release_proof",
        "fallback": True,
    },
}


def hook_admission_report(
    *,
    root: Path,
    layer: str,
    paths: list[Path] | None = None,
    editor_root: Path | None = None,
    require_editor_root: bool = False,
    command: str = "",
    expected_root: Path | None = None,
) -> dict[str, object]:
    normalized_layer = _normalize_layer(layer)
    repo = root.resolve()
    status = workspace_status(repo)
    target_paths = _target_paths(repo, paths or [])
    base = {
        "ok": True,
        "state": "admitted",
        "layer": normalized_layer,
        "hook": HOOK_LAYERS[normalized_layer],
        "target_root": repo.as_posix(),
        "expected_root": expected_root.resolve().as_posix() if expected_root else repo.as_posix(),
        "role": status["role"],
        "branch": status["branch"],
        "editor_root": editor_root.resolve().as_posix() if editor_root else "",
        "target_paths": [path.as_posix() for path in target_paths],
        "decision": {"action": "allow", "reason": "hook_admitted"},
        "required_gaps": [],
    }
    if normalized_layer == "context":
        return _context_report(base, repo=repo, expected_root=expected_root)
    if normalized_layer == "pre-tool":
        if status["role"] in PROTECTED_WRITE_ROLES and not target_paths:
            return _blocked(base, "protected_root_pretool_paths_required")
        return _prewrite_report(
            base,
            repo=repo,
            paths=target_paths,
            editor_root=editor_root,
            require_editor_root=require_editor_root,
        )
    if normalized_layer == "pre-run":
        return _pre_run_report(
            base,
            repo=repo,
            paths=target_paths,
            editor_root=editor_root,
            require_editor_root=require_editor_root,
            command=command,
        )
    if normalized_layer == "post-write":
        return _post_write_report(base, repo=repo, expected_paths=target_paths)
    return _fallback_report(base)


def push_admission_report(
    *,
    root: Path,
    target_ref: str,
    pushed_head: str,
    remote_head: str = "",
) -> dict[str, object]:
    """Admit or block a push whose destination is a protected role.

    The push tail is the last place a raw `git push` can move an accepted/candidate
    ref without the executed-proof precondition that `land` enforces. This binds the
    same reducer to the pre-push boundary: pushing to a protected branch requires an
    executed proof bound to the exact pushed HEAD. Pushes to unprotected refs (work
    lanes, feature branches) are admitted untouched.
    """
    from ethos.adapters.mutation.core import proof_gaps
    from ethos_core.contracts.branch.roles import load_branch_role_policy

    repo = root.resolve()
    policy = load_branch_role_policy(repo)
    branch = target_ref.removeprefix("refs/heads/")
    role = policy.role_for_branch(branch)
    identity_report = push_identity_policy_report(
        root=repo, pushed_head=pushed_head, remote_head=remote_head
    )
    identity_gaps = list(cast("list[str]", identity_report["required_gaps"]))
    base = {
        "ok": True,
        "state": "admitted",
        "hook": "pre-push",
        "target_ref": target_ref,
        "target_branch": branch,
        "role": role,
        "pushed_head": pushed_head,
        "remote_head": remote_head,
        "identity_policy": identity_report,
        "decision": {"action": "allow", "reason": "push_admitted"},
        "required_gaps": [],
    }
    proof_required = role in PROTECTED_WRITE_ROLES
    proof_required_gaps = proof_gaps(repo, pushed_head) if proof_required else []
    # The push plane must enforce the SAME candidate-train topology as the local ref-move
    # reducer, or a raw `git push --force <proven-old-sha>:dev` rewinds/side-steps the
    # accepted branch that ref_move_admission_report blocks (the pushed head is proven but
    # not the live candidate head / not a fast-forward). remote_head is the accepted
    # old-value, pushed_head the new. Only the accepted branch carries this invariant;
    # the candidate branch's proof gate is already covered above.
    topology_gaps = (
        accepted_advance_gaps(repo, policy, old_value=remote_head, new_value=pushed_head)
        if branch == policy.accepted_branch
        else []
    )
    gaps = [*identity_gaps, *proof_required_gaps, *topology_gaps]
    if gaps:
        reason = (
            "push_to_protected_role_not_proven"
            if proof_required_gaps or topology_gaps
            else "pushed_commit_identity_not_allowed"
        )
        base.update(
            ok=False,
            state="blocked",
            required_gaps=gaps,
            decision={"action": "block", "reason": reason},
        )
    return base


_ZERO_OID = "0" * 40


def _proof_evidence_digest(root: Path, head: str) -> str:
    """The evidence_digest of the VALID executed proof at head, or '' if none.

    Lets the closeout-intent marker bind to the exact proof this transition carries: a
    marker minted for a different proof cannot authorize this move."""
    record = executed_proof_record(root, head)
    if not isinstance(record, dict):
        return ""
    return str(record.get("evidence_digest", ""))


def accepted_advance_gaps(
    repo: Path,
    policy: BranchRolePolicy,
    *,
    old_value: str,
    new_value: str,
) -> list[str]:
    """Topology gaps for an advance of the accepted branch to `new_value`.

    The candidate-train invariant — the accepted branch only ever advances to the LIVE
    candidate head, by a fast-forward — is enforced HERE so BOTH the local ref-move
    reducer and the push reducer share one definition. Emits, distinctly:
      * accepted_advance_not_candidate_validated: new_value is not contained in candidate
      * accepted_ref_move_not_candidate_head: contained but != the live candidate head
      * accepted_ref_move_not_fast_forward: old_value is not an ancestor of new_value
    Proof and closeout-intent are NOT included — proof is added by each caller, and the
    marker is a local-only signal a push cannot carry. old_value all-zeros (ref creation)
    skips only the fast-forward check (==candidate_head still pins the target).
    """
    candidate_branch = policy.candidate_branch
    gaps: list[str] = []
    contained = subprocess.run(
        ["git", "merge-base", "--is-ancestor", new_value, candidate_branch],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    candidate_head = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", candidate_branch],
        cwd=repo,
        capture_output=True,
        check=False,
        text=True,
    ).stdout.strip()
    if contained.returncode != 0:
        gaps.append("accepted_advance_not_candidate_validated")
    elif new_value != candidate_head:
        gaps.append("accepted_ref_move_not_candidate_head")
    if old_value not in (_ZERO_OID, ""):
        fast_forward = subprocess.run(
            ["git", "merge-base", "--is-ancestor", old_value, new_value],
            cwd=repo,
            capture_output=True,
            check=False,
        )
        if fast_forward.returncode != 0:
            gaps.append("accepted_ref_move_not_fast_forward")
    return gaps


def ref_move_admission_report(
    *,
    root: Path,
    ref_name: str,
    old_value: str,
    new_value: str,
) -> dict[str, object]:
    """Admit or block a LOCAL ref update (merge / branch -f / reset / ff / commit).

    The candidate train's load-bearing invariant is that the accepted branch may only
    ever advance to a commit the candidate branch already contains — work is validated
    on candidate BEFORE it is accepted. `ethos land`/`land --closeout` enforce that
    two-stage path, but a raw `git merge --ff-only work/x dev` (or `git branch -f dev
    <sha>`, `git reset --hard`) moves the accepted ref directly, skipping candidate —
    and nothing stopped it, because the commit/push hooks guard writes and pushes, not
    local ref moves. That reachable-but-forbidden transition is the bug: ETHOS must make
    an unvalidated accepted-branch advance UNREACHABLE, not merely discouraged.

    Bound to git's reference-transaction hook (which fires on every ref change), this
    enforces, for a move of the accepted branch:
      (1) candidate-first: new_value must be contained in the candidate branch, and
      (2) proven: an executed proof must bind new_value.
    Deletions, creations, no-ops, and moves of non-accepted refs are admitted. The
    sanctioned `ethos land --closeout` path satisfies (1)+(2) by construction, so only
    out-of-band ref moves are blocked.
    """
    from ethos.adapters.mutation.core import proof_gaps
    from ethos_core.contracts.branch.roles import load_branch_role_policy

    repo = root.resolve()
    policy = load_branch_role_policy(repo)
    branch = ref_name.removeprefix("refs/heads/")
    zero = "0" * 40
    base = {
        "ok": True,
        "state": "admitted",
        "hook": "reference-transaction",
        "ref": ref_name,
        "branch": branch,
        "old_value": old_value,
        "new_value": new_value,
        "decision": {"action": "allow", "reason": "ref_move_admitted"},
        "required_gaps": [],
    }
    if new_value in (zero, "") or new_value == old_value:
        return base

    gaps: list[str] = []
    reason = ""
    if branch == policy.accepted_branch:
        # Topology invariant (contained + ==candidate_head + fast-forward) is shared with
        # the push reducer via accepted_advance_gaps, so a raw ref move and a raw push are
        # judged identically. Proof and the closeout-intent marker are added below — proof
        # binds both planes, but the marker is a local-only "is this my closeout?" signal.
        gaps.extend(accepted_advance_gaps(repo, policy, old_value=old_value, new_value=new_value))
        gaps.extend(proof_gaps(repo, new_value))
        # Official-closeout discrimination (R12 load-bearing nail): the substantive
        # checks above cannot tell an official `ethos land --closeout` apart from a raw
        # `git update-ref` to the same proven candidate head — both are byte-identical.
        # Require a one-shot closeout-intent marker written by official closeout for the
        # EXACT transition. A raw ref move carries none -> no_closeout_intent (a marker
        # for a different move -> mismatch; an expired one -> stale; a reused nonce -> no
        # marker again). The marker is consumed here but does NOT admit: it only proves
        # "this is my process's closeout"; legality is still the checks above (R19 — the
        # marker is a local discipline layer, not a trust root; forge re-execution is).
        intent = consume_closeout_intent(
            root=repo,
            ref_name=ref_name,
            old_value=old_value,
            new_value=new_value,
            expect=MarkerExpectation(
                evidence_digest=_proof_evidence_digest(repo, new_value),
                gate_policy_digest=gate_policy_digest(repo),
            ),
        )
        if intent["gap"]:
            gaps.append(str(intent["gap"]))
        reason = "accepted_ref_move_bypasses_candidate_train"
    elif branch == policy.candidate_branch:
        gaps.extend(proof_gaps(repo, new_value))
        reason = "protected_ref_move_not_proven"
    else:
        return base
    if gaps:
        base.update(
            ok=False,
            state="blocked",
            required_gaps=gaps,
            decision={"action": "block", "reason": reason},
        )
    return base


def work_lane_ref_transition_report(
    *,
    root: Path,
    phase: str,
    ref_name: str,
    old_value: str,
    new_value: str,
) -> dict[str, object]:
    """Check or record one Work Lane ref transition against its current lease.

    ``prepared`` is the blocking admission point. ``committed`` updates ignored
    local coordination after Git has won; failure there is repair-required rather
    than an atomic rollback claim.
    """
    repo = root.resolve()
    status = workspace_status(repo)
    branch = ref_name.removeprefix("refs/heads/")
    if old_value in {_ZERO_OID, ""}:
        return {
            "ok": True,
            "state": "admitted",
            "phase": phase,
            "ref": ref_name,
            "branch": branch,
            "old_value": old_value,
            "new_value": new_value,
            "lease": {},
            "decision": {"action": "allow", "reason": "lane_creation_saga_started"},
            "required_gaps": [],
        }
    worktrees = cast("list[dict[str, str]]", status.get("worktrees", []))
    leases = leases_by_branch(worktrees, current_path=repo)
    lease = leases.get(branch, {})
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    gaps = _work_lane_lease_transition_gaps(
        branch=branch,
        lease=lease,
        actor=actor,
        old_value=old_value,
    )
    base: dict[str, object] = {
        "ok": not gaps,
        "state": "admitted" if not gaps else "blocked",
        "phase": phase,
        "ref": ref_name,
        "branch": branch,
        "old_value": old_value,
        "new_value": new_value,
        "lease": lease,
        "decision": {
            "action": "allow" if not gaps else "block",
            "reason": "work_lane_ref_transition_admitted"
            if not gaps
            else "work_lane_ref_transition_stale",
        },
        "required_gaps": gaps,
    }
    if gaps or phase != "committed":
        return base
    try:
        updated = advance_lease_head(
            _control_state_db(status, repo),
            subject=branch,
            holder_ref=actor,
            expected_lease_id=str(lease.get("lease_id") or lease.get("id") or ""),
            expected_epoch=integer_value(lease.get("epoch")),
            old_head=old_value,
            new_head=new_value,
        )
    except ValueError as exc:
        gap = str(exc)
        return {
            **base,
            "ok": False,
            "state": "repair_required",
            "decision": {"action": "block", "reason": "lease_head_update_failed"},
            "required_gaps": [gap],
        }
    return {
        **base,
        "state": "lease_head_advanced",
        "lease": updated,
        "decision": {"action": "allow", "reason": "lease_head_advanced"},
    }


def _work_lane_lease_transition_gaps(
    *, branch: str, lease: dict[str, object], actor: str, old_value: str
) -> list[str]:
    gaps: list[str] = []
    if not lease:
        return [f"work_lane_missing_lease:{branch}"]
    if str(lease.get("normalization_state") or "") != "normalized":
        gaps.append(f"lane_lease_legacy_ambiguous:{branch}")
    holder = str(lease.get("holder_ref") or "")
    if not holder or holder != actor:
        gaps.append(f"lease_holder_mismatch:{branch}")
    if not str(lease.get("lease_id") or "") or integer_value(lease.get("epoch")) < 1:
        gaps.append(f"lease_generation_missing:{branch}")
    expected_head = str(lease.get("expected_head") or "")
    if expected_head != old_value:
        gaps.append(f"lease_head_stale:{expected_head}!={old_value}")
    return gaps


def _control_state_db(status: dict[str, object], repo: Path) -> Path:
    for worktree in cast("list[dict[str, str]]", status.get("worktrees", [])):
        if worktree.get("role") == "accepted_root" and worktree.get("path"):
            return Path(worktree["path"]) / ".ethos" / "state" / "state.sqlite"
    return repo / ".ethos" / "state" / "state.sqlite"


def _normalize_layer(layer: str) -> str:
    normalized = layer.strip().lower().replace("_", "-")
    if normalized not in HOOK_LAYERS:
        return "pre-tool"
    return normalized


def _target_paths(root: Path, paths: list[Path]) -> list[Path]:
    return [
        path
        if path.is_absolute() or has_invalid_path_token_character(path.as_posix())
        else root / path
        for path in paths
    ]


def _context_report(
    base: dict[str, object],
    *,
    repo: Path,
    expected_root: Path | None,
) -> dict[str, object]:
    if expected_root is not None and expected_root.resolve() != repo:
        return _blocked(base, "hook_context_root_mismatch")
    base["state"] = "refreshed"
    base["decision"] = {"action": "allow", "reason": "context_refreshed"}
    return base


def _prewrite_report(
    base: dict[str, object],
    *,
    repo: Path,
    paths: list[Path],
    editor_root: Path | None,
    require_editor_root: bool,
) -> dict[str, object]:
    admission = prewrite_guard(
        root=repo,
        paths=paths,
        editor_root=editor_root,
        require_editor_root=require_editor_root,
    )
    base["admission"] = admission
    base["role"] = admission["role"]
    base["branch"] = admission["branch"]
    if admission["ok"] is True:
        base["state"] = "admitted"
        base["decision"] = {"action": "allow", "reason": "prewrite_admitted"}
        return base
    blocked = _blocked(base, str(admission["error"]))
    blocked["next_actions"] = _prewrite_block_next_actions(admission)
    return blocked


def _pre_run_report(
    base: dict[str, object],
    *,
    repo: Path,
    paths: list[Path],
    editor_root: Path | None,
    require_editor_root: bool,
    command: str,
) -> dict[str, object]:
    stash_policy = git_stash_policy(command)
    risk = command_risk(command, role=str(base["role"]))
    base["command"] = command
    base["command_risk"] = risk
    base["git_stash_policy"] = stash_policy
    if stash_policy["forbidden"] is True:
        return _blocked(base, "git_stash_forbidden")
    if risk["tracked_mutation_risk"] is not True:
        base["state"] = "admitted"
        base["decision"] = {"action": "allow", "reason": "command_observe_only"}
        return base
    if not paths:
        return _blocked(base, "hook_prerun_paths_required")
    return _prewrite_report(
        base,
        repo=repo,
        paths=paths,
        editor_root=editor_root,
        require_editor_root=require_editor_root,
    )


def _post_write_report(
    base: dict[str, object],
    *,
    repo: Path,
    expected_paths: list[Path],
) -> dict[str, object]:
    status = workspace_status(repo)
    changed_paths = _string_list(status.get("changed_paths"))
    base["role"] = status["role"]
    base["branch"] = status["branch"]
    base["changed_paths"] = changed_paths
    expected = {_relative(repo, path) for path in expected_paths}
    unexpected = [path for path in changed_paths if not expected or path not in expected]
    base["unexpected_paths"] = unexpected
    if status["role"] in PROTECTED_WRITE_ROLES and changed_paths:
        return _fused(base, "post_write_protected_root_dirty")
    if unexpected:
        return _fused(base, "post_write_unexpected_path")
    base["state"] = "admitted"
    base["decision"] = {"action": "allow", "reason": "post_write_expected_paths_clean"}
    return base


def _relative(root: Path, path: Path) -> str:
    resolved = path if path.is_absolute() else root / path
    try:
        return resolved.resolve().relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item) for item in value]


def _fallback_report(base: dict[str, object]) -> dict[str, object]:
    base["state"] = "fallback"
    base["decision"] = {"action": "allow", "reason": "fallback_hook_layer"}
    base["fallback"] = True
    return base


def _prewrite_block_next_actions(admission: dict[str, object]) -> list[str]:
    lease = admission.get("work_lane_lease")
    if isinstance(lease, dict) and str(lease.get("reason") or "").startswith(
        "lease_holder_mismatch:"
    ):
        holder_ref = str(lease.get("holder_ref") or "").strip()
        if holder_ref:
            return [
                f"set ETHOS_ACTOR={holder_ref} and rerun the blocked command, or obtain handoff",
                "ethos lane prewrite <path>",
            ]
        return ["set ETHOS_ACTOR to the current holder_ref or obtain handoff"]
    if isinstance(lease, dict) and str(lease.get("reason") or "").startswith(
        "work_lane_missing_lease:"
    ):
        return ["ethos lane start <name> --holder-ref <holder-ref> --apply --json"]
    return ["ethos lane prewrite <path>"]


def _blocked(base: dict[str, object], reason: str) -> dict[str, object]:
    base["ok"] = False
    base["state"] = "blocked"
    base["decision"] = {"action": "block", "reason": reason}
    base["required_gaps"] = [reason]
    return base


def _fused(base: dict[str, object], reason: str) -> dict[str, object]:
    base["ok"] = False
    base["state"] = "fused"
    base["decision"] = {"action": "fuse", "reason": reason}
    base["required_gaps"] = [reason]
    return base
