"""Migrate declared legacy branch identities through exact Git and Lease effects.

The rename changes no content: one ref transaction creates each standard role ref at
the head of the legacy ref it replaces and deletes that legacy ref, and every
worktree bound to a renamed ref is then bound to its new name. A closeout that the
binding step did not finish binds those worktrees before it does anything else.
"""

from __future__ import annotations

import os
import shlex
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.admission.role_rename import RENAMED_ROLES
from ethos.adapters.admission.role_rename import ROLE_RENAME_OPERATION
from ethos.adapters.admission.role_rename import legacy_role_names
from ethos.adapters.admission.role_rename import legacy_role_renames
from ethos.adapters.admission.role_rename import require_owned_topic
from ethos.adapters.admission.role_rename import retained_topic_target
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import recover_plan
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_object import zero_oid
from ethos.adapters.store.state.lease.lifecycle.effects import migrate_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import declared_role_names
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ethos.adapters.store.state.lease.projection import LeaseRow
    from ethos.contracts.plan import TransitionPlan


def rename_retained_topic(root: Path, *, apply: bool) -> dict[str, object] | None:
    """Migrate only the caller's retained topic, recovering projections from its attested CAS."""
    report: dict[str, object] = {
        "verdict": "block",
        "state": "blocked",
        "applied": False,
        "required_gaps": [],
        "next_action": "ethos lane repair-paradigm --apply --json",
    }
    selected = None
    try:
        selected = _topic_transition(root)
        if selected is None:
            return None
        source, target, head, plan = selected
        report.update(head=head, renames={f"refs/heads/{source}": f"refs/heads/{target}"})
        row = require_owned_topic(root, source, target, recovering=plan is not None)
        plan = _topic_plan(root, source, target, head, row, plan)
        if not apply:
            return {**report, "verdict": "pass", "state": "ready_to_rename"}
        if ref_head(root, source):
            execute_git_effect(root, plan, issuer=row.holder_ref)
        report.update(state="partial_transition", applied=True)
        _require_topic_poststate(root, source, target, head)
        bind_renamed_worktrees(root, {f"refs/heads/{source}": f"refs/heads/{target}"})
        request = LeaseOperationRequest(
            operation="rename",
            branch=source,
            holder_ref=row.holder_ref,
            generation=row.generation,
            expires_at=row.expires_at,
            apply=True,
        )
        migrated = migrate_lease(
            state_database(root),
            request=request,
            target=target,
            recheck=lambda: _require_topic_binding(root, source, target, head),
        )
    except (OSError, TypeError, ValueError) as error:
        if apply and selected is not None:
            source, target, head, _plan = selected
            if not ref_head(root, source) and ref_head(root, target) == head:
                report.update(state="partial_transition", applied=True)
        return {**report, "required_gaps": [str(error)]}
    return {
        **report,
        "verdict": "pass",
        "state": "topic_identity_migrated",
        "lease": migrated,
        "next_action": "ethos status --json",
    }


def _topic_plan(
    root: Path,
    source: str,
    target: str,
    head: str,
    row: LeaseRow,
    recovered: TransitionPlan | None,
) -> TransitionPlan:
    """Bind a new rename to fresh coordination, or recheck the exact recovered binding."""
    generation = asdict(row)
    if recovered is not None:
        if (
            recovered.policy.get("worktree") != root.resolve().as_posix()
            or mutable_json(recovered.facts.get("values", {}).get("lease_generation")) != generation
        ):
            message = "retained_topic_recovery_binding_stale"
            raise ValueError(message)
        return recovered
    if ref_head(root, target):
        message = f"legacy_role_rename_target_exists:{target}"
        raise ValueError(message)
    zero = zero_oid(root)
    plan = compile_observed_git_effect(
        root,
        None,
        GitEffect(
            updates={
                f"refs/heads/{source}": GitRefUpdate(expected=head, desired=zero),
                f"refs/heads/{target}": GitRefUpdate(expected=zero, desired=head),
            }
        ),
        head=head,
        policy={
            "operation": ROLE_RENAME_OPERATION,
            "actor": row.holder_ref,
            "execution_branch": source,
            "worktree": root.resolve().as_posix(),
        },
        values={"lease_generation": generation},
    )
    admit_git_effect(root, plan)
    return plan


def _topic_transition(root: Path) -> tuple[str, str, str, TransitionPlan | None] | None:
    """Select a declared retained topic or the exact interrupted identity projection."""
    bound = git_stdout(root, "symbolic-ref", "--quiet", "HEAD").removeprefix("refs/heads/")
    if not bound:
        return None
    head = ref_head(root, f"refs/heads/{bound}")
    if not head:
        return _recover_topic_transition(root, bound)
    target = retained_topic_target(root, bound, head)
    if target:
        return bound, target, head, None
    standard = BranchRolePolicy()
    prefix = declared_role_names(committed_file_text(root, head, ".ethos/workspace.toml")).get(
        "work_branch_prefix", ""
    )
    if not prefix or not bound.startswith(standard.work_branch_prefix):
        return None
    source = prefix + bound.removeprefix(standard.work_branch_prefix)
    if (
        retained_topic_target(root, source, head) != bound
        or ref_head(root, source)
        or observe_lease(state_database(root), source).state == "missing"
    ):
        return None
    return _recover_topic_transition(root, source)


def _recover_topic_transition(root: Path, source: str) -> tuple[str, str, str, TransitionPlan]:
    """Validate the sole attested rename and its current ref postimage before recovery."""
    zero = zero_oid(root)
    plan = recover_plan(
        root, operation=ROLE_RENAME_OPERATION, desired=zero, ref_name=f"refs/heads/{source}"
    )
    if plan is None:
        message = "retained_topic_recovery_unproven"
        raise ValueError(message)
    effect = git_effect_from_plan(plan)
    created = [
        (ref, update.desired) for ref, update in effect.updates.items() if update.expected == zero
    ]
    if len(created) != 1:
        message = "retained_topic_recovery_scope_mismatch"
        raise ValueError(message)
    target, head = created[0][0].removeprefix("refs/heads/"), created[0][1]
    expected = GitEffect(
        updates={
            f"refs/heads/{source}": GitRefUpdate(expected=head, desired=zero),
            f"refs/heads/{target}": GitRefUpdate(expected=zero, desired=head),
        }
    )
    if effect != expected or retained_topic_target(root, source, head) != target:
        message = "retained_topic_recovery_scope_mismatch"
        raise ValueError(message)
    return source, target, head, plan


def _require_topic_poststate(root: Path, source: str, target: str, head: str) -> None:
    """Observe the exact ref postimage again before each dependent projection."""
    if ref_head(root, source) or ref_head(root, target) != head:
        msg = "retained_topic_ref_poststate_stale"
        raise ValueError(msg)


def _require_topic_binding(root: Path, source: str, target: str, head: str) -> None:
    """Require the exact native binding immediately around the Lease CAS."""
    _require_topic_poststate(root, source, target, head)
    if git_stdout(root, "symbolic-ref", "--quiet", "HEAD") != f"refs/heads/{target}":
        msg = "retained_topic_worktree_projection_incomplete"
        raise ValueError(msg)


def rename_legacy_roles(
    root: Path,
    *,
    current_head: str,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
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
        return {
            **report,
            "verdict": "pass",
            "state": "ready_to_rename",
            "required_gaps": [],
        }
    attestation = execute_git_effect(
        root,
        plan,
        issuer=os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos",
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
    """Select renamed worktrees once, then freshly recheck only each affected binding."""
    for block in git_stdout(root, "worktree", "list", "--porcelain").split("\n\n"):
        fields = dict(line.partition(" ")[::2] for line in block.splitlines())
        selected = fields.get("branch", "")
        if selected not in renames:
            continue
        path = Path(fields.get("worktree", ""))
        bound = run_git(path, "symbolic-ref", "--quiet", "HEAD", check=False).stdout.strip()
        if bound != selected or not ref_head(root, renames[selected]):
            message = "branch_role_worktree_binding_stale"
            raise ValueError(message)
        if not ref_head(root, bound):
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
