"""Accepted closeout renames legacy role refs to the names the paradigm fixes.

The rename changes no content: one ref transaction creates each standard role ref at
the head of the legacy ref it replaces and deletes that legacy ref, and every
worktree bound to a renamed ref is then bound to its new name. A closeout that the
binding step did not finish binds those worktrees before it does anything else.
"""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.admission.role_rename import RENAMED_ROLES
from ethos.adapters.admission.role_rename import ROLE_RENAME_OPERATION
from ethos.adapters.admission.role_rename import legacy_role_names
from ethos.adapters.admission.role_rename import legacy_role_renames
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import declared_role_names
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from collections.abc import Mapping


def rename_legacy_roles(
    root: Path, *, current_head: str, apply: bool, authorized: bool, expect_head: str | None
) -> dict[str, object] | None:
    """Rename the legacy role refs from the accepted root, or return None when none remain.

    The accepted root runs the rename under whichever name the committed table gives it, so a
    table that names only its release branch under a legacy name renames it from `dev`.
    """
    try:
        renames = legacy_role_renames(root, current_head)
        names = legacy_role_names(committed_file_text(root, current_head, ".ethos/workspace.toml"))
    except (TypeError, ValueError):
        return None
    accepted = names.get("accepted_branch", BranchRolePolicy().accepted_branch)
    if not renames or current_branch(root) != accepted:
        return None
    targets = {legacy: target for legacy, (target, _head) in renames.items()}
    gaps = _rename_gaps(root, current_head, renames, authorized=authorized, expect_head=expect_head)
    report: dict[str, object] = {
        "verdict": "block",
        "state": "blocked",
        "head": current_head,
        "renames": targets,
        "required_gaps": gaps,
        "next_action": _closeout_command(root, current_head),
    }
    if gaps:
        return report
    zero = "0" * len(current_head)
    updates: dict[str, GitRefUpdate] = {}
    for legacy, (target, head) in renames.items():
        updates[legacy] = GitRefUpdate(expected=head, desired=zero)
        updates[target] = GitRefUpdate(expected=zero, desired=head)
    plan = compile_observed_git_effect(
        root,
        None,
        GitEffect(updates=updates),
        head=current_head,
        policy={"operation": ROLE_RENAME_OPERATION},
    )
    if not apply:
        admit_git_effect(root, plan)
        return {**report, "verdict": "pass", "state": "ready_to_rename", "required_gaps": []}
    attestation = execute_git_effect(
        root, plan, issuer=os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"
    )
    bind_renamed_worktrees(root, targets)
    return {
        **report,
        "verdict": "pass",
        "state": "branch_roles_renamed",
        "required_gaps": [],
        "attestation": attestation.model_dump(mode="json"),
        "next_action": "ethos status --json",
    }


def bind_renamed_worktrees(root: Path, renames: Mapping[str, str]) -> None:
    """Bind every worktree whose HEAD names a removed legacy role ref to its new name."""
    for block in git_stdout(root, "worktree", "list", "--porcelain").split("\n\n"):
        fields = dict(line.partition(" ")[::2] for line in block.splitlines())
        path = Path(fields.get("worktree", ""))
        bound = run_git(path, "symbolic-ref", "--quiet", "HEAD", check=False).stdout.strip()
        if bound in renames and not ref_head(root, bound):
            run_git(path, "symbolic-ref", "HEAD", renames[bound])


def resume_renamed_bindings(root: Path) -> None:
    """Bind a worktree left on a renamed legacy role ref, using its own declared names."""
    bound = run_git(root, "symbolic-ref", "--quiet", "HEAD", check=False).stdout.strip()
    workspace = root / ".ethos" / "workspace.toml"
    if not bound or ref_head(root, bound) or not workspace.is_file():
        return
    try:
        declared = declared_role_names(workspace.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return
    standard = BranchRolePolicy()
    bind_renamed_worktrees(
        root,
        {
            f"refs/heads/{declared[role]}": f"refs/heads/{getattr(standard, role)}"
            for role in RENAMED_ROLES
            if role in declared and ref_head(root, f"refs/heads/{getattr(standard, role)}")
        },
    )


def _rename_gaps(
    root: Path,
    head: str,
    renames: Mapping[str, tuple[str, str]],
    *,
    authorized: bool,
    expect_head: str | None,
) -> list[str]:
    """Admit a rename only by authority, at the expected head, onto absent standard refs."""
    declared = declared_role_names(committed_file_text(root, head, ".ethos/workspace.toml"))
    standard = BranchRolePolicy()
    retired = {
        declared.get(field, getattr(standard, field))
        for field in ("work_branch_prefix", "proposal_branch_prefix")
    } - {standard.work_branch_prefix, standard.proposal_branch_prefix}
    return [
        *(["authorization_required"] if not authorized else []),
        *(["expected_head_mismatch"] if expect_head != head else []),
        *(
            f"legacy_role_rename_target_exists:{target.removeprefix('refs/heads/')}"
            for target, _head in renames.values()
            if ref_head(root, target)
        ),
        *(
            f"legacy_role_rename_topic_refs_present:{prefix}"
            for prefix in sorted(retired)
            if git_stdout(root, "for-each-ref", "--format=%(refname)", f"refs/heads/{prefix}")
        ),
    ]


def _closeout_command(root: Path, head: str) -> str:
    """Return the exact closeout invocation that renames this accepted root's role refs."""
    return (
        f"ethos land --closeout --apply --authorize --expect-head {head} "
        f"--root {shlex.quote(root.resolve().as_posix())} --json"
    )
