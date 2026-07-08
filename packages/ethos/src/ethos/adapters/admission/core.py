from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.branch_roles import PROTECTED_WRITE_ROLES

if TYPE_CHECKING:
    from pathlib import Path

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

_MUTATION_PATTERNS = (
    " write_text(",
    ".write_text(",
    " >",
    ">>",
    " tee ",
    "sed -i",
    "python -c",
    "rm ",
    "mv ",
    "cp ",
)


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
            admitted_reason="prewrite_admitted",
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
) -> dict[str, object]:
    """Admit or block a push whose destination is a protected role.

    The push tail is the last place a raw `git push` can move an accepted/candidate
    ref without the executed-proof precondition that `land` enforces. This binds the
    same reducer to the pre-push boundary: pushing to a protected branch requires an
    executed proof bound to the exact pushed HEAD. Pushes to unprotected refs (work
    lanes, feature branches) are admitted untouched.
    """
    from ethos.adapters.mutation.core import _proof_gaps
    from ethos_core.contracts.branch_roles import load_branch_role_policy

    repo = root.resolve()
    policy = load_branch_role_policy(repo)
    branch = target_ref.removeprefix("refs/heads/")
    role = policy.role_for_branch(branch)
    base = {
        "ok": True,
        "state": "admitted",
        "hook": "pre-push",
        "target_ref": target_ref,
        "target_branch": branch,
        "role": role,
        "pushed_head": pushed_head,
        "decision": {"action": "allow", "reason": "push_admitted"},
        "required_gaps": [],
    }
    if role not in PROTECTED_WRITE_ROLES:
        return base
    gaps = _proof_gaps(repo, pushed_head)
    if gaps:
        base.update(
            ok=False,
            state="blocked",
            required_gaps=gaps,
            decision={"action": "block", "reason": "push_to_protected_role_not_proven"},
        )
    return base


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
    import subprocess

    from ethos.adapters.mutation.core import _proof_gaps
    from ethos_core.contracts.branch_roles import load_branch_role_policy

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
    if branch != policy.accepted_branch or new_value in (zero, "") or new_value == old_value:
        return base

    gaps: list[str] = []
    contained = subprocess.run(
        ["git", "merge-base", "--is-ancestor", new_value, policy.candidate_branch],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    if contained.returncode != 0:
        gaps.append("accepted_advance_not_candidate_validated")
    gaps.extend(_proof_gaps(repo, new_value))
    if gaps:
        base.update(
            ok=False,
            state="blocked",
            required_gaps=gaps,
            decision={"action": "block", "reason": "accepted_ref_move_bypasses_candidate_train"},
        )
    return base


def _normalize_layer(layer: str) -> str:
    normalized = layer.strip().lower().replace("_", "-")
    if normalized not in HOOK_LAYERS:
        return "pre-tool"
    return normalized


def _target_paths(root: Path, paths: list[Path]) -> list[Path]:
    return [path if path.is_absolute() else root / path for path in paths]


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
    admitted_reason: str,
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
        base["decision"] = {"action": "allow", "reason": admitted_reason}
        return base
    return _blocked(base, str(admission["error"]))


def _pre_run_report(
    base: dict[str, object],
    *,
    repo: Path,
    paths: list[Path],
    editor_root: Path | None,
    require_editor_root: bool,
    command: str,
) -> dict[str, object]:
    stash_policy = _git_stash_policy(command)
    risk = _command_risk(command)
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
        admitted_reason="prewrite_admitted",
    )


def _command_risk(command: str) -> dict[str, object]:
    lowered = f" {command.lower()} "
    risky = any(pattern in lowered for pattern in _MUTATION_PATTERNS)
    return {
        "tracked_mutation_risk": risky,
        "reason": "command_text_matches_mutation_pattern" if risky else "observe_only_command",
    }


def _git_stash_policy(command: str) -> dict[str, object]:
    tokens = _shell_tokens(command)
    operation = _git_stash_operation(tokens)
    if operation is None:
        return {"forbidden": False, "operation": "", "reason": "not_git_stash"}
    if operation in {"list", "show"}:
        return {"forbidden": False, "operation": operation, "reason": "observe_only_stash_read"}
    return {
        "forbidden": True,
        "operation": operation,
        "reason": "stash_is_hidden_change_carrier",
    }


def _shell_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _git_stash_operation(tokens: list[str]) -> str | None:
    for index, token in enumerate(tokens):
        if token != "git":
            continue
        stash_index = _find_git_subcommand(tokens, start=index + 1)
        if stash_index is None or tokens[stash_index] != "stash":
            continue
        if stash_index + 1 >= len(tokens) or tokens[stash_index + 1].startswith("-"):
            return "push"
        return tokens[stash_index + 1]
    return None


def _find_git_subcommand(tokens: list[str], *, start: int) -> int | None:
    index = start
    while index < len(tokens):
        token = tokens[index]
        if token in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}:
            index += 2
            continue
        if token.startswith(("--git-dir=", "--work-tree=", "--namespace=", "--exec-path=")):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        return index
    return None


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
