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
from ethos.adapters.mutation.accepted.legacy_role_observation import LeaseSnapshot
from ethos.adapters.mutation.accepted.legacy_role_observation import RenameSnapshot
from ethos.adapters.mutation.accepted.legacy_role_observation import WorktreeSnapshot
from ethos.adapters.mutation.accepted.legacy_role_observation import prepared_snapshot
from ethos.adapters.mutation.accepted.legacy_role_observation import preserved_content
from ethos.adapters.mutation.accepted.legacy_role_observation import worktree_fields
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import records as ref_effect_records
from ethos.adapters.repo.git_effect_attestation import validate as validate_ref_effect
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.store.state.lease.lifecycle.transitions import rename_exact_leases
from ethos.adapters.store.state.lease.projection import observe_lease
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
    bound = run_git(root, "symbolic-ref", "--quiet", "HEAD", check=False).stdout.strip()
    pending = (
        _pending_rename(root, expect_head, expect_state)
        if expect_state or (bound and not ref_head(root, bound))
        else None
    )
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
    snapshot = _rename_snapshot(root, targets)
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
    matches = []
    for item in members:
        if item.predicate != "observation:branch-roles-rename":
            continue
        body = item.payload.body
        if body.get("root") != root.resolve().as_posix() or body.get("head") != head:
            continue
        completed = any(
            record.predicate == "effect:branch-roles-rename"
            and record.payload.body.get("prepared") == item.id
            for record in members
        )
        if not completed or body.get("state_digest") == state:
            matches.append((item, completed))
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
    report = {
        "head": body["head"],
        "renames": targets,
        "state_digest": state,
        "verdict": "block",
        "state": "blocked",
        "required_gaps": [],
        "next_action": _closeout_command(root, str(body["head"]), state),
    }
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
        _require_snapshot(root, snapshot, targets, completed=completed)
        if completed_refs:
            _require_ref_result(root, plan, effect)
    except ValueError as error:
        return {**report, "required_gaps": [str(error)]}
    if completed:
        return {
            **report,
            "verdict": "pass",
            "state": "branch_roles_renamed",
            "next_action": "ethos status --json",
        }
    if not apply:
        return {**report, "verdict": "pass", "state": "ready_to_resume_rename"}
    leases = {
        source: (str(record["target"]), record["lease"])
        for source, record in snapshot["leases"].items()
    }
    attestation = rename_exact_leases(
        state_database(root),
        renames=leases,
        transition=lambda: _materialize_rename(root, plan, snapshot, targets),
    )
    if attestation is None:
        return {**report, "verdict": "pass", "state": "branch_roles_materialization_pending"}
    _require_snapshot(root, snapshot, targets)
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
    return {
        **report,
        "verdict": "pass",
        "state": "branch_roles_renamed",
        "required_gaps": [],
        "attestation": attestation.model_dump(mode="json"),
        "next_action": "ethos status --json",
    }


def _materialize_rename(
    root: Path, plan: TransitionPlan, snapshot: RenameSnapshot, targets: Mapping[str, str]
) -> Attestation | None:
    """Recheck and bind the carried ref effect while the Lease writer transaction is held."""
    effect = git_effect_from_plan(plan)
    completed = _require_ref_state(root, effect)
    _require_snapshot(root, snapshot, targets)
    if completed:
        _require_ref_result(root, plan, effect)
        bind_renamed_worktrees(root, targets)
    result = execute_git_effect(root, plan, issuer=_actor())
    if not _require_ref_state(root, effect):
        raise ValueError(_STATE_STALE)
    _require_snapshot(root, snapshot, targets)
    bind_renamed_worktrees(root, targets)
    _require_snapshot(root, snapshot, targets)
    return (
        result
        if all(
            record.get("branch") == snapshot["worktrees"][record["worktree"]]["target"]
            for record in worktree_fields(root)
            if record["worktree"] in snapshot["worktrees"]
        )
        else None
    )


def _require_ref_result(root: Path, plan: TransitionPlan, effect: GitEffect) -> None:
    """Require the original completed ref evidence before restoring a missing binding."""
    records = ref_effect_records(root, plan)
    if not records:
        message = "legacy_role_rename_outcome_unproven"
        raise ValueError(message)
    for recorded in records:
        validate_ref_effect(
            root, effect, recorded, issuer=_actor(), plan=plan, current_postconditions=False
        )


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


def _rename_snapshot(root: Path, targets: Mapping[str, str]) -> RenameSnapshot:
    """Observe only selected worktree bindings and exact coordination, without writes."""
    worktrees: dict[str, WorktreeSnapshot] = {}
    leases: dict[str, LeaseSnapshot] = {}
    for record in worktree_fields(root):
        bound = record.get("branch", "")
        if bound in targets:
            path = Path(record["worktree"])
            if path.is_symlink() or "locked" in record or "prunable" in record:
                raise ValueError(_WORKTREE_UNSAFE)
            worktrees[path.resolve().as_posix()] = {
                "source": bound,
                "target": targets[bound],
                "head": ref_head(root, bound),
                "content": preserved_content(path),
            }
    for source, target in targets.items():
        source_lane, target_lane = (
            source.removeprefix("refs/heads/"),
            target.removeprefix("refs/heads/"),
        )
        old = observe_lease(state_database(root), source_lane)
        new = observe_lease(state_database(root), target_lane)
        if new.state != "missing" or old.state == "unknown":
            message = f"legacy_role_rename_lease_conflict:{source_lane}"
            raise ValueError(message)
        if target_lane.startswith("work/") and old.state != "valid":
            message = f"work_lane_lease_{old.state}:{source_lane}"
            raise ValueError(message)
        leases[source_lane] = {"target": target_lane, "lease": old.record()}
    return {"worktrees": worktrees, "leases": leases}


def _require_snapshot(
    root: Path, snapshot: RenameSnapshot, targets: Mapping[str, str], *, completed: bool = False
) -> None:
    """Accept only the original bytes and an old or exact new binding/Lease, never drift."""
    records = worktree_fields(root)
    selected = {
        record["worktree"]: record
        for record in records
        if record.get("branch") in {*targets, *targets.values()}
    }
    worktrees = snapshot["worktrees"]
    if set(selected) != set(worktrees):
        raise ValueError(_STATE_STALE)
    for path, before in worktrees.items():
        record = selected[path]
        if (
            record.get("branch") not in {before["source"], before["target"]}
            or (completed and record.get("branch") != before["target"])
            or ref_head(root, record["branch"]) not in {"", before["head"]}
            or Path(path).is_symlink()
            or "locked" in record
            or "prunable" in record
            or preserved_content(Path(path)) != before["content"]
        ):
            raise ValueError(_STATE_STALE)
    for source, before in snapshot["leases"].items():
        old = observe_lease(state_database(root), source)
        new = observe_lease(state_database(root), before["target"])
        expected = before["lease"]
        if "lane_ref" not in expected:
            if old.record() != expected or new.state != "missing":
                raise ValueError(_STATE_STALE)
            continue
        post = {
            "lane_ref": before["target"],
            "holder_ref": expected["holder_ref"],
            "generation": int(expected["generation"]) + 1,
            "expires_at": expected["expires_at"],
        }
        if not (
            (not completed and old.record() == expected and new.state == "missing")
            or (
                old.state == "missing"
                and new.state == "valid"
                and new.lease is not None
                and new.lease.to_payload() == post
            )
        ):
            raise ValueError(_STATE_STALE)


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


def _closeout_command(root: Path, head: str, state: str = "") -> str:
    """Return the exact closeout invocation that renames this accepted root's role refs."""
    return (
        f"ethos land --closeout --apply --authorize --expect-head {head} "
        f"{f'--expect-state {state} ' if state else ''}"
        f"--root {shlex.quote(root.resolve().as_posix())} --json"
    )
