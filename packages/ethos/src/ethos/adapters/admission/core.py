from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.closeout_intent.core import consume_closeout_intent
from ethos.adapters.admission.prewrite import has_control_character
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.admission.shell import command_risk
from ethos.adapters.admission.shell import git_stash_policy
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.branch.roles import PROTECTED_WRITE_ROLES

if TYPE_CHECKING:
    from pathlib import Path

_COMMIT_IDENTITY_FIELD_COUNT = 4

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
    gaps = [*identity_gaps, *proof_required_gaps]
    if gaps:
        reason = (
            "push_to_protected_role_not_proven"
            if proof_required_gaps
            else "pushed_commit_identity_not_allowed"
        )
        base.update(
            ok=False,
            state="blocked",
            required_gaps=gaps,
            decision={"action": "block", "reason": reason},
        )
    return base


def _git_config(root: Path, key: str) -> str:
    completed = subprocess.run(
        ["git", "config", "--get", key],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def _commit_exists(root: Path, revision: str) -> bool:
    if not revision or revision == "0" * 40:
        return False
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    return completed.returncode == 0


def _pushed_commit_range(root: Path, *, pushed_head: str, remote_head: str) -> list[str]:
    if not _commit_exists(root, pushed_head):
        return []
    revspec = pushed_head
    if _commit_exists(root, remote_head):
        revspec = f"{remote_head}..{pushed_head}"
    completed = subprocess.run(
        ["git", "rev-list", revspec],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line]


def _commit_identity(root: Path, revision: str) -> dict[str, str]:
    completed = subprocess.run(
        ["git", "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", revision],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    parts = completed.stdout.rstrip("\n").split("\x00")
    if completed.returncode != 0 or len(parts) != _COMMIT_IDENTITY_FIELD_COUNT:
        return {"author_name": "", "author_email": "", "committer_name": "", "committer_email": ""}
    return {
        "author_name": parts[0],
        "author_email": parts[1],
        "committer_name": parts[2],
        "committer_email": parts[3],
    }


def push_identity_policy_report(
    *, root: Path, pushed_head: str, remote_head: str = ""
) -> dict[str, object]:
    """Report optional push-range Git identity admission.

    The mechanism is intentionally repository-local and opt-in: ETHOS remains
    organization-native and does not hardcode a product author. Repositories that
    need a canonical forge identity enable ``ethos.pushIdentityPolicy`` in local or
    repo config. ``configured-user`` means every newly pushed commit must have both
    author and committer equal to the checkout's configured ``user.name`` and
    ``user.email``.
    """
    mode = _git_config(root, "ethos.pushIdentityPolicy")
    if mode != "configured-user":
        return {
            "ok": True,
            "mode": mode or "disabled",
            "expected_identity": "",
            "checked_commit_count": 0,
            "violations": [],
            "required_gaps": [],
        }
    expected_name = _git_config(root, "user.name")
    expected_email = _git_config(root, "user.email")
    expected_identity = (
        f"{expected_name} <{expected_email}>" if expected_name or expected_email else ""
    )
    gaps: list[str] = []
    violations: list[dict[str, str]] = []
    if not expected_name:
        gaps.append("push_identity_user_name_missing")
    if not expected_email:
        gaps.append("push_identity_user_email_missing")
    head_exists = _commit_exists(root, pushed_head)
    commits = (
        _pushed_commit_range(root, pushed_head=pushed_head, remote_head=remote_head)
        if head_exists
        else []
    )
    if pushed_head and not head_exists:
        gaps.append("push_identity_commit_range_unreadable")
    for commit in commits:
        identity = _commit_identity(root, commit)
        author_ok = (
            identity["author_name"] == expected_name and identity["author_email"] == expected_email
        )
        committer_ok = (
            identity["committer_name"] == expected_name
            and identity["committer_email"] == expected_email
        )
        if author_ok and committer_ok:
            continue
        violation = {
            "commit": commit,
            "author": f"{identity['author_name']} <{identity['author_email']}>",
            "committer": f"{identity['committer_name']} <{identity['committer_email']}>",
        }
        violations.append(violation)
        if not author_ok:
            gaps.append(f"pushed_commit_author_not_configured_identity:{commit}")
        if not committer_ok:
            gaps.append(f"pushed_commit_committer_not_configured_identity:{commit}")
    return {
        "ok": not gaps,
        "mode": mode,
        "expected_identity": expected_identity,
        "checked_commit_count": len(commits),
        "violations": violations,
        "required_gaps": gaps,
    }


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
        # The accepted branch may only ever advance to the LIVE candidate head, by a
        # fast-forward, carrying a complete executed proof. Three escapes exist even when
        # a commit is candidate-related AND proven, so each is checked distinctly:
        #   * not candidate-validated: new_value is not contained in the candidate branch
        #     at all — work that never went through the train (existing invariant).
        #   * not candidate-head: new_value IS candidate-contained but is an intermediate
        #     commit, not the live candidate head. Only the head the train validated may
        #     be promoted; an ancestor of it was never a tip a closeout would accept.
        #   * not fast-forward: old_value is not an ancestor of new_value — a rollback to
        #     an older (still candidate-contained, still proven) commit rewinds accepted
        #     history out of band. `git merge --ff-only` gives the sanctioned closeout
        #     this for free.
        #   * proof gaps: new_value lacks a complete executed proof (see proof_gaps).
        contained = subprocess.run(
            ["git", "merge-base", "--is-ancestor", new_value, policy.candidate_branch],
            cwd=repo,
            capture_output=True,
            check=False,
        )
        candidate_head = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", policy.candidate_branch],
            cwd=repo,
            capture_output=True,
            check=False,
            text=True,
        ).stdout.strip()
        if contained.returncode != 0:
            gaps.append("accepted_advance_not_candidate_validated")
        elif new_value != candidate_head:
            gaps.append("accepted_ref_move_not_candidate_head")
        if old_value not in (zero, ""):
            fast_forward = subprocess.run(
                ["git", "merge-base", "--is-ancestor", old_value, new_value],
                cwd=repo,
                capture_output=True,
                check=False,
            )
            if fast_forward.returncode != 0:
                gaps.append("accepted_ref_move_not_fast_forward")
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
            root=repo, ref_name=ref_name, old_value=old_value, new_value=new_value
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


def _normalize_layer(layer: str) -> str:
    normalized = layer.strip().lower().replace("_", "-")
    if normalized not in HOOK_LAYERS:
        return "pre-tool"
    return normalized


def _target_paths(root: Path, paths: list[Path]) -> list[Path]:
    return [
        path if path.is_absolute() or has_control_character(path.as_posix()) else root / path
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
    changed_paths = [str(path) for path in status["changed_paths"]]
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


def _fallback_report(base: dict[str, object]) -> dict[str, object]:
    base["state"] = "fallback"
    base["decision"] = {"action": "allow", "reason": "fallback_hook_layer"}
    base["fallback"] = True
    return base


def _prewrite_block_next_actions(admission: dict[str, object]) -> list[str]:
    lease = admission.get("work_lane_lease")
    if isinstance(lease, dict) and str(lease.get("reason") or "").startswith(
        "work_lane_actor_mismatch:"
    ):
        owner = str(lease.get("owner") or "").strip()
        if owner:
            return [
                f"set ETHOS_ACTOR={owner} and rerun the blocked command, or obtain lane handoff",
                "ethos lane prewrite <path>",
            ]
        return ["set ETHOS_ACTOR to the lane lease owner or obtain handoff"]
    if isinstance(lease, dict) and str(lease.get("reason") or "").startswith(
        "work_lane_missing_lease:"
    ):
        return ["ethos lane start <name> --owner <owner> --apply --json"]
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
