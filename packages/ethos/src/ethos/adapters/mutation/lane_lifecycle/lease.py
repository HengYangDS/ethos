"""Product operations over generation-bound local Lane Leases.

These operations bind one exact request to Git and ignored SQLite observations.
They coordinate cooperative writers; they do not mint identity or authority.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import cast

from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.core import accept_lease_handoff
from ethos.adapters.store.state.lease.lifecycle.core import offer_lease_handoff
from ethos.adapters.store.state.lease.lifecycle.core import renew_lease
from ethos.adapters.store.state.lease.lifecycle.core import resume_lease
from ethos.adapters.store.state.lease.projection import integer_value
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.coordination import HolderRef
from ethos_core.contracts.lifecycle.core import LeaseFacts
from ethos_core.contracts.lifecycle.core import MutationRequest
from ethos_core.contracts.lifecycle.core import lease_transition
from ethos_core.contracts.lifecycle.core import reduce_lease_request

_LEASE_EFFECTS = {
    "renew": (renew_lease, "holder_ref expected_epoch ttl_seconds"),
    "resume": (resume_lease, "holder_ref expected_epoch ttl_seconds"),
    "handoff_offer": (
        offer_lease_handoff,
        "holder_ref expected_epoch target_holder_ref",
    ),
    "handoff_accept": (
        accept_lease_handoff,
        "target_holder_ref offer_id expected_epoch holder_quiesced ttl_seconds",
    ),
}


def renew_work_lane_lease(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    root: Path,
    branch: str,
    holder_ref: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    ttl_seconds: int,
    apply: bool,
) -> dict[str, object]:
    """Renew one exact, unexpired local lease generation."""
    return _lease_lifecycle_operation("renew", locals())


def resume_work_lane_lease(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    root: Path,
    branch: str,
    holder_ref: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    ttl_seconds: int,
    contrary_decision: bool,
    apply: bool,
) -> dict[str, object]:
    """Resume one expired lease only for its previous holder and generation."""
    return _lease_lifecycle_operation(
        "resume",
        locals()
        | {"extra_gaps": ("lease_resume_blocked_by_decision",) if contrary_decision else ()},
    )


def offer_work_lane_handoff(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    root: Path,
    branch: str,
    holder_ref: str,
    target_holder_ref: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    apply: bool,
) -> dict[str, object]:
    """Offer one local holder handoff without changing the current holder."""
    return _lease_lifecycle_operation("handoff_offer", locals())


def accept_work_lane_handoff(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    root: Path,
    branch: str,
    target_holder_ref: str,
    offer_id: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    holder_quiesced: bool,
    ttl_seconds: int,
    apply: bool,
) -> dict[str, object]:
    """Accept one exact offer and replace the local holder plus generation."""
    return _lease_lifecycle_operation(
        "handoff_accept",
        locals()
        | {
            "holder_ref": target_holder_ref,
            "confirmation_present": holder_quiesced,
            "extra_gaps": () if holder_quiesced else ("holder_quiescence_confirmation_required",),
        },
    )


def _lease_lifecycle_operation(operation: str, values: dict[str, Any]) -> dict[str, object]:
    root = cast("Path", values["root"])
    branch = str(values["branch"])
    lease_id = str(values["lease_id"])
    epoch = cast("int | None", values.get("epoch"))
    expect_head = str(values["expect_head"])
    ttl_seconds = cast("int", values.get("ttl_seconds", 86_400))
    apply = bool(values["apply"])
    repo = repo_root(root)
    status = workspace_status(repo)
    expected_state, holder_gaps = _lease_expected_state(
        repo,
        values,
    )
    transition = lease_transition(operation)
    evaluation = reduce_lease_request(
        transition,
        LeaseFacts(
            role=str(status.get("role") or ""),
            current_branch=str(status.get("branch") or ""),
            current_head=run_git(repo, "rev-parse", "HEAD").stdout.strip(),
            branch=branch,
            expect_head=expect_head,
            lease_id=lease_id,
            epoch=epoch,
            ttl_seconds=ttl_seconds,
            offer_id=str(values.get("offer_id") or ""),
            apply=apply,
            initial_gaps=cast("tuple[str, ...]", values.get("extra_gaps", ())) + holder_gaps,
        ),
    )
    request = MutationRequest(
        command=f"lane-{operation.replace('_', '-')}",
        apply=apply,
        authorized=bool(values.get("confirmation_present")),
        expect_head=expect_head or None,
    )
    result: dict[str, object] = {
        "ok": evaluation.ok,
        "state": evaluation.state,
        "branch": branch,
        "lease": {},
        "handoff_offer": {},
        "receipt": {},
        "required_gaps": list(evaluation.gaps),
    }
    if apply and evaluation.ok:
        try:
            effect = _apply_lease_effect(
                operation,
                state_root(status, repo) / ".ethos" / "state" / "state.sqlite",
                expected_state,
                values,
            )
        except ValueError as exc:
            result.update(ok=False, state="blocked", required_gaps=[str(exc)])
        else:
            result["handoff_offer" if operation == "handoff_offer" else "lease"] = effect
            result["state"] = transition.applied_state
            result["receipt"] = _lease_operation_receipt(
                operation=operation,
                branch=branch,
                effect=effect,
            )
    result["mutation"] = mutation_envelope(
        request,
        action=f"lane.lease.{operation.replace('_', '.')}",
        resource=f"refs/heads/{branch}",
        expected_state=expected_state,
        verdict=cast("Any", "allow" if result["ok"] else "block"),
        required_gaps=tuple(map(str, cast("list[object]", result["required_gaps"]))),
        why=(str(result["state"]),) if result["ok"] else (),
        state=str(result["state"]),
        identity_basis="holder_ref_equality",
        evidence_boundary="current_git_and_local_lease_observation",
        enforcement_boundary="local_sqlite_compare_and_swap",
        verifier_provenance="current_worktree_runner",
    )
    return result


def _lease_expected_state(
    repo: Path, values: dict[str, Any]
) -> tuple[dict[str, object], tuple[str, ...]]:
    expected_state: dict[str, object] = {
        "root": repo.resolve().as_posix(),
        "branch": str(values["branch"]),
        "head": str(values["expect_head"]),
        "holder_ref": str(values["holder_ref"]),
        "lease_id": str(values["lease_id"]),
        "epoch": cast("int | None", values.get("epoch")) or 0,
        "target_holder_ref": str(values.get("target_holder_ref") or ""),
        "offer_id": str(values.get("offer_id") or ""),
    }
    try:
        for field in ("holder_ref", "target_holder_ref"):
            value = str(expected_state[field])
            if value or field == "holder_ref":
                expected_state[field] = HolderRef.parse(value).serialize()
    except ValueError:
        return expected_state, ("holder_ref_invalid",)
    return expected_state, ()


def _apply_lease_effect(
    operation: str,
    db_path: Path,
    expected_state: dict[str, object],
    values: dict[str, Any],
) -> dict[str, object]:
    try:
        handler, fields = _LEASE_EFFECTS[operation]
    except KeyError:
        raise ValueError(f"lease_operation_unknown:{operation}") from None  # noqa: EM102, RUF100 - machine-readable gap token is the exception contract
    arguments = {
        "holder_ref": str(expected_state["holder_ref"]),
        "target_holder_ref": str(expected_state["target_holder_ref"]),
        "offer_id": str(values.get("offer_id") or ""),
        "expected_epoch": cast("int | None", values.get("epoch")) or 0,
        "holder_quiesced": bool(values.get("holder_quiesced")),
        "ttl_seconds": cast("int", values.get("ttl_seconds", 86_400)),
    }
    return cast("Any", handler)(
        db_path,
        subject=str(values["branch"]),
        expected_lease_id=str(values["lease_id"]),
        expected_head=str(values["expect_head"]),
        **{field: arguments[field] for field in fields.split()},
    )


def state_root(status: dict[str, object], default_root: Path) -> Path:
    """Resolve the accepted checkout that owns Git-common-directory local state."""
    worktrees = status.get("worktrees")
    if isinstance(worktrees, list):
        for worktree in worktrees:
            if not isinstance(worktree, dict):
                continue
            payload = cast("dict[str, object]", worktree)
            if payload.get("role") == ROLE_ACCEPTED_ROOT and payload.get("path"):
                return Path(str(payload["path"]))
    return default_root


def _lease_operation_receipt(
    *, operation: str, branch: str, effect: dict[str, object]
) -> dict[str, object]:
    return {
        "receipt_id": f"receipt:{operation}:{effect.get('lease_id') or effect.get('offer_id')}",
        "operation": operation.replace("handoff_", "handoff-"),
        "branch": branch,
        "applied": True,
        "lease_id": str(effect.get("lease_id") or ""),
        "epoch": integer_value(effect.get("epoch")),
        "expected_head": str(effect.get("expected_head") or ""),
        "mints_authority": False,
        "transferable": False,
    }
