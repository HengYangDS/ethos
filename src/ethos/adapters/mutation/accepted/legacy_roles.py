"""Accepted closeout renames legacy role refs to the names the paradigm fixes.

The rename changes no content: one ref transaction creates each standard role ref at
the head of the legacy ref it replaces and deletes that legacy ref, and every
worktree bound to a renamed ref is then bound to its new name. A closeout that the
binding step did not finish binds those worktrees before it does anything else.
"""

from __future__ import annotations

import os
import shlex
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.admission.role_rename import ROLE_RENAME_OPERATION
from ethos.adapters.admission.role_rename import legacy_role_names
from ethos.adapters.admission.role_rename import legacy_role_renames
from ethos.adapters.mutation.accepted.legacy_role_observation import RenameSnapshot
from ethos.adapters.mutation.accepted.legacy_role_observation import observe_snapshot
from ethos.adapters.mutation.accepted.legacy_role_observation import prepared_snapshot
from ethos.adapters.mutation.accepted.legacy_role_observation import worktree_fields
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import validated_plan_attestation
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.store.state.lease.lifecycle.transitions import rename_exact_leases
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest

if TYPE_CHECKING:
    from collections.abc import Mapping

_STATE_STALE = "legacy_role_rename_state_stale"
_WORKTREE_UNSAFE = "legacy_role_rename_worktree_unsafe"


def rename_legacy_roles(
    root: Path,
    *,
    current_head: str,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    expect_state: str | None = None,
) -> dict[str, object] | None:
    """Rename the legacy role refs from the accepted root, or return None when none remain.

    The accepted root runs the rename under whichever name the committed table gives it, so a
    table that names only its release branch under a legacy name renames it from `dev`.
    """
    pending = _pending_rename(root, expect_head, expect_state)
    if pending:
        prepared, completed = pending
        return _finish_rename(
            root,
            prepared,
            apply=apply,
            authorized=authorized,
            expect_head=expect_head,
            expect_state=expect_state,
            completed=completed,
        )
    try:
        renames = legacy_role_renames(root, current_head)
        names = legacy_role_names(committed_file_text(root, current_head, ".ethos/workspace.toml"))
    except (TypeError, ValueError):
        renames, names = {}, {}
    accepted = names.get("accepted_branch", BranchRolePolicy().accepted_branch)
    if not renames or current_branch(root) != accepted:
        return None
    targets = {legacy: target for legacy, (target, _head) in renames.items()}
    gaps = _rename_gaps(root, current_head, renames, authorized=authorized, expect_head=expect_head)
    report = _rename_report(root, current_head, targets)
    if gaps:
        return {**report, "required_gaps": gaps}
    snapshot = observe_snapshot(root, targets)
    state = canonical_json_digest({"head": current_head, "renames": renames, "snapshot": snapshot})
    report.update(state_digest=state, next_action=_closeout_command(root, current_head, state))
    topics = any(
        ref.startswith(("refs/heads/work/", "refs/heads/proposal/")) for ref in targets.values()
    )
    state_gaps = (
        ["legacy_role_rename_state_stale"]
        if expect_state is not None and expect_state != state
        else []
    )
    if apply and topics and expect_state is None:
        state_gaps.append("expected_state_required")
    if state_gaps:
        return {**report, "required_gaps": state_gaps}
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
        values={
            "role_rename_snapshot": snapshot,
            "role_rename_state": state,
            "role_renames": targets,
        },
    )
    admit_git_effect(root, plan)
    if not apply:
        return {**report, "verdict": "pass", "state": "ready_to_rename", "required_gaps": []}
    body: dict[str, object] = {
        "root": root.resolve().as_posix(),
        "head": current_head,
        "state_digest": state,
        "plan": plan.model_dump(mode="json"),
    }
    prepared = _record("observation:branch-roles-rename", body, state, plan_digest=plan.digest)
    record_attestations(root, (prepared,))
    return _finish_rename(
        root,
        prepared,
        apply=True,
        authorized=authorized,
        expect_head=expect_head,
        expect_state=state,
    )


def _actor() -> str:
    return os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"


def _record(
    predicate: str, body: dict[str, object], state: str, *, plan_digest: str | None = None
) -> Attestation:
    """Record hashes and the original native plan, never file bytes or fresh authority."""
    now = datetime.now(UTC)
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": predicate,
            "verifier": _actor(),
            "subject": f"branch-roles:{state}",
            "issued_at": now,
            "valid_from": now,
            "valid_until": None,
            "verdict": "pass",
            "payload": {"kind": "observation:native", "body": body},
            "relations": (),
            "advisories": (),
            "evidence_refs": (),
            "commitment_digest": None,
            "facts_digest": None,
            "plan_digest": plan_digest,
            "policy_digest": None,
            "effect_digest": state,
            "mints_authority": False,
        }
    )


def _pending_rename(
    root: Path, head: str | None, state: str | None
) -> tuple[Attestation, bool] | None:
    """Select an unresolved original operation, never a fresh permission."""
    members = read_attestation_set(root)[1]
    completed = {
        record.payload.body.get("prepared")
        for record in members
        if record.predicate == "effect:branch-roles-rename"
    }
    matches = [
        (item, item.id in completed)
        for item in members
        if item.predicate == "observation:branch-roles-rename"
        and item.payload.body.get("root") == root.resolve().as_posix()
        and item.payload.body.get("head") == head
        and (item.id not in completed or item.payload.body.get("state_digest") == state)
    ]
    if len(matches) > 1:
        message = "legacy_role_rename_recovery_ambiguous"
        raise ValueError(message)
    return matches[0] if matches else None


def _finish_rename(
    root: Path,
    prepared: Attestation,
    *,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    expect_state: str | None,
    completed: bool = False,
) -> dict[str, object]:
    """Recover only the carried exact ref, binding and coordination transition."""
    body = prepared.payload.body
    plan, snapshot, targets = prepared_snapshot(prepared)
    effect = git_effect_from_plan(plan)
    state = str(body["state_digest"])
    report = _rename_report(root, str(body["head"]), targets, state)
    gaps = ["authorization_required"] if not authorized else []
    if expect_head != body["head"] or prepared.verifier != _actor():
        gaps.append("legacy_role_rename_authority_stale")
    topics = any(
        target.startswith(("refs/heads/work/", "refs/heads/proposal/"))
        for target in targets.values()
    )
    if expect_state != state and (expect_state is not None or topics):
        gaps.append("legacy_role_rename_state_stale")
    if gaps:
        return {**report, "required_gaps": gaps}
    try:
        completed_refs = _require_ref_state(root, effect, completed=completed)
        observe_snapshot(root, targets, original=snapshot, completed=completed)
        if completed_refs:
            _require_ref_result(root, plan)
    except ValueError as error:
        return {**report, "required_gaps": [str(error)]}
    if completed or not apply:
        report.update(
            verdict="pass", state="branch_roles_renamed" if completed else "ready_to_resume_rename"
        )
        if completed:
            report["next_action"] = "ethos status --json"
        return report
    attestation = rename_exact_leases(
        state_database(root),
        renames={
            source: (record["target"], record["lease"])
            for source, record in snapshot["leases"].items()
        },
        transition=lambda: _materialize_rename(root, plan, snapshot, targets),
    )
    if attestation is None:
        return {**report, "verdict": "pass", "state": "branch_roles_materialization_pending"}
    observe_snapshot(root, targets, original=snapshot)
    terminal = _record(
        "effect:branch-roles-rename",
        {
            "prepared": prepared.id,
            "ref_effect": attestation.id,
            "state": "completed",
            "state_digest": state,
        },
        state,
    )
    record_attestations(root, (terminal,))
    report.update(
        verdict="pass",
        state="branch_roles_renamed",
        attestation=attestation.model_dump(mode="json"),
        next_action="ethos status --json",
    )
    return report


def _materialize_rename(
    root: Path, plan: TransitionPlan, snapshot: RenameSnapshot, targets: Mapping[str, str]
) -> Attestation | None:
    """Recheck and bind the carried ref effect while the Lease writer transaction is held."""
    effect = git_effect_from_plan(plan)
    completed = _require_ref_state(root, effect)
    observe_snapshot(root, targets, original=snapshot)
    if completed:
        _require_ref_result(root, plan)
        bind_renamed_worktrees(root, targets)
    result = execute_git_effect(root, plan, issuer=_actor())
    if not _require_ref_state(root, effect):
        raise ValueError(_STATE_STALE)
    observe_snapshot(root, targets, original=snapshot)
    bind_renamed_worktrees(root, targets)
    observe_snapshot(root, targets, original=snapshot)
    return (
        result
        if all(
            record.get("branch") == snapshot["worktrees"][record["worktree"]]["target"]
            for record in worktree_fields(root)
            if record["worktree"] in snapshot["worktrees"]
        )
        else None
    )


def _require_ref_result(root: Path, plan: TransitionPlan) -> None:
    """Select original exact ref evidence through its native historical verifier."""
    if (
        not (selected := validated_plan_attestation(root, plan.digest, issuer=_actor()))
        or selected[0] != plan
    ):
        message = "legacy_role_rename_outcome_unproven"
        raise ValueError(message)


def _require_ref_state(root: Path, effect: GitEffect, *, completed: bool = False) -> bool:
    """Require the whole original ref preimage or postimage, including during preview."""
    observed = {
        ref: ref_head(root, ref) or "0" * len(update.expected)
        for ref, update in effect.updates.items()
    }
    before = {ref: update.expected for ref, update in effect.updates.items()}
    after = {ref: update.desired for ref, update in effect.updates.items()}
    if observed not in (before, after) or (completed and observed != after):
        raise ValueError(_STATE_STALE)
    return observed == after


def bind_renamed_worktrees(root: Path, renames: Mapping[str, str]) -> None:
    """Bind every worktree whose HEAD names a removed legacy role ref to its new name."""
    for fields in worktree_fields(root):
        path = Path(fields.get("worktree", ""))
        bound = run_git(path, "symbolic-ref", "--quiet", "HEAD", check=False).stdout.strip()
        if bound in renames and not ref_head(root, bound):
            run_git(path, "symbolic-ref", "HEAD", renames[bound])


def _rename_gaps(
    root: Path,
    head: str,
    renames: Mapping[str, tuple[str, str]],
    *,
    authorized: bool,
    expect_head: str | None,
) -> list[str]:
    """Admit a rename only by authority, at the expected head, onto absent standard refs."""
    return [
        *(["authorization_required"] if not authorized else []),
        *(["expected_head_mismatch"] if expect_head != head else []),
        *(
            f"legacy_role_rename_target_exists:{target.removeprefix('refs/heads/')}"
            for target, _head in renames.values()
            if ref_head(root, target)
        ),
        *(
            ["legacy_role_rename_targets_ambiguous"]
            if len({target for target, _head in renames.values()}) != len(renames)
            else []
        ),
    ]


def _rename_report(
    root: Path, head: str, targets: Mapping[str, str], state: str = ""
) -> dict[str, object]:
    """Project one unchanged envelope for initial admission and exact recovery."""
    return {
        "verdict": "block",
        "state": "blocked",
        "head": head,
        "renames": targets,
        "required_gaps": [],
        "next_action": _closeout_command(root, head, state),
        **({"state_digest": state} if state else {}),
    }


def _closeout_command(root: Path, head: str, state: str = "") -> str:
    """Return the exact closeout invocation that renames this accepted root's role refs."""
    return (
        f"ethos land --closeout --apply --authorize --expect-head {head} "
        f"{f'--expect-state {state} ' if state else ''}"
        f"--root {shlex.quote(root.resolve().as_posix())} --json"
    )
