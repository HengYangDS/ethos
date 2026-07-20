"""Native exceptional retirement of one accepted-policy-bound unbound Work Lane ref."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from typing import NamedTuple
from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation
import ethos.adapters.mutation.lane_retirement.unbound.policy.core as policy
import ethos.adapters.mutation.lane_retirement.unbound.records.core as records
import ethos.adapters.mutation.lane_retirement.unbound.reporting.core as reporting
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.store.state.lease.lifecycle.core import expected_current_lease
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_owner_unavailable_lease
from ethos.adapters.store.state.schema import initialize_state

type _Controls = dict[str, Any]


class _LeaseRevokeArguments(NamedTuple):
    subject: str
    holder_ref: str
    expected_lease_id: str
    expected_epoch: int
    expected_head: str


def _data(**values: Any) -> dict[str, Any]:
    return values


def _write(path: Path, payload: dict[str, object], kind: str) -> tuple[str, str]:
    try:
        return records.write_record(path, payload, kind=kind), ""
    except (OSError, TypeError, ValueError) as exc:
        return "", records.stable_gap(exc)


def _blocked(result: dict[str, object], gaps: list[str], **context: object) -> dict[str, object]:
    return reporting.blocked(result | context, gaps)


def _admission_gaps(
    repo: Path, *, observed: dict[str, object], controls: _Controls, apply: bool | None = None
) -> list[str]:
    return policy.admission_gaps(
        repo,
        branch=controls["branch"],
        expect_head=controls["expect_head"],
        reason=controls["reason"],
        apply=controls["apply"] if apply is None else apply,
        authorized=controls["authorized"],
        break_glass=controls["break_glass"],
        confirm_irreversible=controls["confirm_irreversible"],
        observed=observed,
    )


def retire_unbound_work_lane_ref(  # noqa: PLR0913, RUF100 - exact retirement protocol shape
    *,
    root: Path,
    branch: str,
    expect_head: str | None = None,
    reason: str = "",
    chronicle_ref: str = "",
    apply: bool = False,
    authorized: bool = False,
    break_glass: bool = False,
    confirm_irreversible: bool = False,
    owner_unavailable_recovery: bool = False,
) -> dict[str, object]:
    """Retire exactly one accepted-policy-bound unbound ``work/*`` ref."""
    repo = repo_root(root)
    branch, expected = branch.strip(), (expect_head or "").strip()
    reason, chronicle_ref = reason.strip(), chronicle_ref.strip()
    controls: _Controls = {
        "branch": branch,
        "expect_head": expected,
        "reason": reason,
        "apply": apply,
        "authorized": authorized,
        "break_glass": break_glass,
        "confirm_irreversible": confirm_irreversible,
    }
    before = _observe(repo, branch=branch, chronicle_ref=chronicle_ref)
    holder_ref = lane_retirement_shared.current_holder_ref()
    gaps = _admission_gaps(repo, observed=before, controls=controls)
    gaps.extend(
        policy.lease_recovery_gaps(
            before,
            holder_ref=holder_ref,
            owner_unavailable_recovery=owner_unavailable_recovery,
        )
    )
    result = reporting.report(
        observed=before,
        chronicle_ref=chronicle_ref,
        owner_unavailable_recovery=owner_unavailable_recovery,
        gaps=gaps,
        **controls,
    )
    if gaps or not apply:
        return result
    return _apply_retirement(
        repo=repo,
        before=before,
        result=result,
        controls=controls,
        chronicle_ref=chronicle_ref,
        holder_ref=holder_ref,
        owner_unavailable_recovery=owner_unavailable_recovery,
    )


def _apply_retirement(  # noqa: PLR0913, RUF100 - bound irreversible transition shape
    *,
    repo: Path,
    before: dict[str, object],
    result: dict[str, object],
    controls: _Controls,
    chronicle_ref: str,
    holder_ref: str,
    owner_unavailable_recovery: bool = False,
) -> dict[str, object]:
    """Persist an admitted attempt and recheck it before any irreversible effect."""
    control_root, gap = policy.accepted_control_root(
        cast("dict[str, object]", before["status"]), accepted_head=str(before["accepted_head"])
    )
    if control_root is None:
        return reporting.blocked(result, [gap])
    records_root = control_root.parent / f"{control_root.name}-records"
    operation_id = records.operation_id(
        branch=controls["branch"],
        expect_head=controls["expect_head"],
        accepted_head=str(before["accepted_head"]),
        protected_refs=cast("dict[str, str]", before["protected_refs"]),
        claim_id=str(before["claim_id"]),
        chronicle=observation.chronicle_binding(before),
        reason=controls["reason"],
        observation_sha256=str(before["observation_sha256"]),
    )
    attempt = records.attempt_payload(
        operation_id=operation_id,
        branch=controls["branch"],
        expect_head=controls["expect_head"],
        reason=controls["reason"],
        observation=before,
    )
    attempt_path, gap = _write(
        records.attempt_path(records_root, operation_id), attempt, records.ATTEMPT_KIND
    )
    if gap:
        return reporting.blocked(result, [gap])
    context = _data(attempt_path=attempt_path, operation_id=operation_id)
    pre_effect = _observe(repo, branch=controls["branch"], chronicle_ref=chronicle_ref)
    pre_gaps = _admission_gaps(repo, observed=pre_effect, controls=controls, apply=True)
    pre_gaps.extend(
        policy.lease_recovery_gaps(
            pre_effect,
            holder_ref=holder_ref,
            owner_unavailable_recovery=owner_unavailable_recovery,
        )
    )
    if observation.operation_bindings(before) != observation.operation_bindings(pre_effect):
        pre_gaps.append("unbound_retire_pre_effect_observation_stale")
    if pre_gaps:
        return _blocked(
            result,
            pre_gaps,
            **context,
            observation=observation.public_observation(pre_effect),
        )
    return _relinquish_then_delete(
        repo=repo,
        control_root=control_root,
        records_root=records_root,
        before=before,
        pre_effect=pre_effect,
        result=result,
        context=context,
        controls=controls,
        chronicle_ref=chronicle_ref,
        holder_ref=holder_ref,
        owner_unavailable_recovery=owner_unavailable_recovery,
    )


def _relinquish_then_delete(  # noqa: PLR0913, RUF100 - bound irreversible transition shape
    *,
    repo: Path,
    control_root: Path,
    records_root: Path,
    before: dict[str, object],
    pre_effect: dict[str, object],
    result: dict[str, object],
    context: dict[str, Any],
    controls: _Controls,
    chronicle_ref: str,
    holder_ref: str,
    owner_unavailable_recovery: bool = False,
) -> dict[str, object]:
    """Hold the lease writer lock across exact revocation and atomic ref deletion."""
    database = control_root / ".ethos" / "state" / "state.sqlite"
    try:
        initialize_state(database)
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("pragma foreign_keys = on")
            connection.execute("begin immediate")
            before_delete = _observe(repo, branch=controls["branch"], chronicle_ref=chronicle_ref)
            delete_gaps = _admission_gaps(
                repo, observed=before_delete, controls=controls, apply=True
            )
            delete_gaps.extend(
                policy.lease_recovery_gaps(
                    before_delete,
                    holder_ref=holder_ref,
                    owner_unavailable_recovery=owner_unavailable_recovery,
                )
            )
            if observation.operation_bindings(pre_effect) != observation.operation_bindings(
                before_delete
            ):
                delete_gaps.append("unbound_retire_pre_effect_observation_stale")
            context |= _data(observation=observation.public_observation(before_delete))
            if delete_gaps:
                connection.rollback()
                return _blocked(result, delete_gaps, **context)
            lease_relinquished = relinquish_owned_lease(
                control_root,
                observed=before_delete,
                holder_ref=holder_ref,
                connection=connection,
                owner_unavailable_recovery=owner_unavailable_recovery,
            )
            if lease_relinquished is None:
                connection.rollback()
                return _blocked(result, ["unbound_retire_active_lease"], **context)
            context["lease_relinquished"] = lease_relinquished
            deleted = _delete_ref_transaction(repo, observed=before_delete, controls=controls)
            if deleted.returncode:
                connection.rollback()
                context["lease_relinquish_rolled_back"] = lease_relinquished
                context["lease_relinquished"] = {}
            else:
                restored = _commit_or_restore(connection, repo, controls)
                if restored is not None:
                    context |= _data(
                        lease_relinquish_rolled_back=lease_relinquished,
                        lease_relinquished={},
                        effect=records.effect_summary(deleted),
                        compensation={
                            "command": "git update-ref create-if-absent",
                            "returncode": restored.returncode,
                            "restored": restored.returncode == 0,
                        },
                        observation=observation.public_observation(
                            _observe(
                                repo,
                                branch=controls["branch"],
                                chronicle_ref=chronicle_ref,
                            )
                        ),
                    )
                    gaps = ["unbound_retire_effect_failed"]
                    gaps += ["unbound_retire_ref_restore_failed"] * bool(restored.returncode)
                    return _blocked(result, gaps, **context)
    except sqlite3.Error as exc:
        rolled_back = context.get("lease_relinquished")
        if isinstance(rolled_back, dict) and rolled_back:
            context["lease_relinquish_rolled_back"] = rolled_back
            context["lease_relinquished"] = {}
        context["observation"] = observation.public_observation(
            _observe(repo, branch=controls["branch"], chronicle_ref=chronicle_ref)
        )
        gap = (
            "unbound_retire_active_lease"
            if "locked" in str(exc).lower()
            else "unbound_retire_effect_failed"
        )
        return _blocked(result, [gap], **context)
    after = _observe(repo, branch=controls["branch"], chronicle_ref=chronicle_ref)
    effect = records.effect_summary(deleted)
    context |= _data(effect=effect, observation=observation.public_observation(after))
    post_gaps = policy.post_effect_gaps(before=before, after=after, deleted=deleted)
    if post_gaps:
        return _blocked(result, post_gaps, **context)
    receipt = records.receipt_payload(
        operation_id=context["operation_id"],
        branch=controls["branch"],
        expect_head=controls["expect_head"],
        reason=controls["reason"],
        before=before,
        after=after,
        effect=effect,
        chronicle_unchanged=observation.chronicle_binding(before)
        == observation.chronicle_binding(after),
        lease_relinquished=lease_relinquished,
    )
    receipt_path, gap = _write(
        records.receipt_path(records_root, context["operation_id"]), receipt, records.RECEIPT_KIND
    )
    if gap:
        outcome = _blocked(result, [gap], **context)
    else:
        outcome = (
            result
            | context
            | _data(
                ok=True,
                state="retired_unbound_exceptional",
                receipt_path=receipt_path,
                receipt=receipt,
                required_gaps=[],
                mutation=reporting.mutation(
                    branch=controls["branch"],
                    expect_head=controls["expect_head"],
                    reason=controls["reason"],
                    chronicle_ref=chronicle_ref,
                    apply=True,
                    confirmed=True,
                    observed=after,
                    break_glass=controls["break_glass"],
                    confirm_irreversible=controls["confirm_irreversible"],
                    owner_unavailable_recovery=owner_unavailable_recovery,
                    gaps=[],
                ),
            )
        )
    return outcome


def _commit_or_restore(connection: sqlite3.Connection, repo: Path, controls: _Controls) -> Any:
    try:
        connection.commit()
    except sqlite3.Error:
        connection.rollback()
        ref, head = f"refs/heads/{controls['branch']}", controls["expect_head"]
        return run_git(repo, "update-ref", ref, head, "0" * 40, check=False)
    return None


def _delete_ref_transaction(repo: Path, *, observed: dict[str, object], controls: _Controls) -> Any:
    """Compare-and-delete target while atomically retaining protected-ref CAS guards.

    A same-value ``update`` is Git's atomic compare-and-swap form for a retained ref.
    Unlike a ``verify`` clause, it is unambiguously a no-op to the
    ``reference-transaction`` hook, so it cannot be misclassified as a protected-ref
    deletion.  All retained-ref CAS guards and the target deletion remain one Git
    transaction.
    """
    protected = cast("dict[str, str]", observed["protected_refs"])
    program = "\n".join(
        [
            "start",
            *(f"update refs/heads/{ref} {head} {head}" for ref, head in protected.items()),
            f"delete refs/heads/{controls['branch']} {controls['expect_head']}",
            "prepare",
            "commit",
            "",
        ]
    )
    return run_git(repo, "update-ref", "--stdin", check=False, stdin=program)


def relinquish_owned_lease(
    control_root: Path,
    *,
    observed: dict[str, object],
    holder_ref: str,
    connection: sqlite3.Connection | None = None,
    owner_unavailable_recovery: bool = False,
) -> dict[str, object] | None:
    """Revoke only this actor's exact lease generation within the native transition."""
    if not bool(observed[observation.HAS_ACTIVE_LEASE]):
        return {}
    arguments = _lease_relinquish_arguments(
        observed=observed,
        holder_ref=holder_ref,
        owner_unavailable_recovery=owner_unavailable_recovery,
    )
    if arguments is None:
        return None
    if connection is None:
        return _revoke_lease_from_database(
            control_root, arguments=arguments, owner_unavailable_recovery=owner_unavailable_recovery
        )
    try:
        row, payload = expected_current_lease(
            connection,
            subject=arguments.subject,
            holder_ref=arguments.holder_ref,
            expected_lease_id=arguments.expected_lease_id,
            expected_epoch=arguments.expected_epoch,
            expected_head=arguments.expected_head,
            require_expired=False,
        )
        connection.execute("delete from leases where id = ?", (str(row[0]),))
    except (KeyError, TypeError, ValueError):
        return None
    return _revoked_lease_payload(row=row, payload=payload, arguments=arguments)


def _lease_relinquish_arguments(
    *, observed: dict[str, object], holder_ref: str, owner_unavailable_recovery: bool
) -> _LeaseRevokeArguments | None:
    lease = cast("dict[str, object]", observed["active_lease"])
    epoch = lease.get("epoch")
    source_holder = str(lease.get("holder_ref") or "")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch <= 0:
        return None
    if not owner_unavailable_recovery and source_holder != holder_ref:
        return None
    try:
        return _LeaseRevokeArguments(
            subject=str(observed["branch"]),
            holder_ref=source_holder,
            expected_lease_id=str(lease["lease_id"]),
            expected_epoch=epoch,
            expected_head=str(lease["expected_head"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _revoke_lease_from_database(
    control_root: Path, *, arguments: _LeaseRevokeArguments, owner_unavailable_recovery: bool
) -> dict[str, object] | None:
    database = control_root / ".ethos" / "state" / "state.sqlite"
    if owner_unavailable_recovery:
        return revoke_owner_unavailable_lease(
            database,
            subject=arguments.subject,
            source_holder_ref=arguments.holder_ref,
            expected_lease_id=arguments.expected_lease_id,
            expected_epoch=arguments.expected_epoch,
            expected_head=arguments.expected_head,
        )
    return revoke_lease(
        database,
        subject=arguments.subject,
        holder_ref=arguments.holder_ref,
        expected_lease_id=arguments.expected_lease_id,
        expected_epoch=arguments.expected_epoch,
        expected_head=arguments.expected_head,
    )


def _revoked_lease_payload(
    *,
    row: sqlite3.Row | tuple[Any, ...],
    payload: dict[str, Any],
    arguments: _LeaseRevokeArguments,
) -> dict[str, object]:
    epoch = payload.get("epoch")
    return {
        "revoked": True,
        "subject": arguments.subject,
        "lease_id": str(row[0]),
        "holder_ref": arguments.holder_ref,
        "epoch": epoch if isinstance(epoch, int) and not isinstance(epoch, bool) else 0,
        "expected_head": str(payload.get("expected_head") or ""),
    }


def _observe(repo: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
    """Keep the local seam for observation-drift contract tests."""
    return observation.observe(repo, branch=branch, chronicle_ref=chronicle_ref)
