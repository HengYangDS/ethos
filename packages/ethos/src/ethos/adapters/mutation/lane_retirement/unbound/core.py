"""Native exceptional retirement of one accepted-policy-bound unbound Work Lane ref."""

from pathlib import Path
from typing import Any
from typing import cast

import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation
import ethos.adapters.mutation.lane_retirement.unbound.policy.core as policy
import ethos.adapters.mutation.lane_retirement.unbound.records.core as records
import ethos.adapters.mutation.lane_retirement.unbound.reporting.core as reporting
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git


def _data(**values: Any) -> dict[str, Any]:
    return values


def _write(path: Path, payload: dict[str, object], kind: str) -> tuple[str, str]:
    try:
        return records.write_record(path, payload, kind=kind), ""
    except (OSError, TypeError, ValueError) as exc:
        return "", records.stable_gap(exc)


def _blocked(result: dict[str, object], gaps: list[str], **context: object) -> dict[str, object]:
    return reporting.blocked(result | context, gaps)


def retire_unbound_work_lane_ref(
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
) -> dict[str, object]:
    """Retire exactly one accepted-policy-bound unbound ``work/*`` ref."""
    repo = repo_root(root)
    branch, expected = branch.strip(), (expect_head or "").strip()
    reason, chronicle_ref = reason.strip(), chronicle_ref.strip()
    controls: Any = _data(
        branch=branch,
        expect_head=expected,
        reason=reason,
        apply=apply,
        authorized=authorized,
        break_glass=break_glass,
        confirm_irreversible=confirm_irreversible,
    )
    before = _observe(repo, branch=branch, chronicle_ref=chronicle_ref)
    gaps = policy.admission_gaps(repo, observed=before, **controls)
    result = reporting.report(observed=before, chronicle_ref=chronicle_ref, gaps=gaps, **controls)
    if gaps or not apply:
        return result
    control_root, gap = policy.accepted_control_root(
        cast("dict[str, object]", before["status"]),
        accepted_head=str(before["accepted_head"]),
    )
    if control_root is None:
        return reporting.blocked(result, [gap])
    records_root = control_root.parent / f"{control_root.name}-records"
    operation_id = records.operation_id(
        branch=branch,
        expect_head=expected,
        accepted_head=str(before["accepted_head"]),
        protected_refs=cast("dict[str, str]", before["protected_refs"]),
        claim_id=str(before["claim_id"]),
        chronicle=observation.chronicle_binding(before),
        reason=reason,
        observation_sha256=str(before["observation_sha256"]),
    )
    attempt = records.attempt_payload(
        operation_id=operation_id,
        branch=branch,
        expect_head=expected,
        reason=reason,
        observation=before,
    )
    attempt_path, gap = _write(
        records.attempt_path(records_root, operation_id), attempt, records.ATTEMPT_KIND
    )
    if gap:
        return reporting.blocked(result, [gap])
    context = _data(attempt_path=attempt_path, operation_id=operation_id)
    pre_effect = _observe(repo, branch=branch, chronicle_ref=chronicle_ref)
    pre_gaps = policy.admission_gaps(repo, observed=pre_effect, **(controls | {"apply": True}))
    if observation.operation_bindings(before) != observation.operation_bindings(pre_effect):
        pre_gaps.append("unbound_retire_pre_effect_observation_stale")
    if pre_gaps:
        return _blocked(
            result,
            pre_gaps,
            **context,
            observation=observation.public_observation(pre_effect),
        )
    deleted = run_git(repo, "update-ref", "-d", f"refs/heads/{branch}", expected, check=False)
    after = _observe(repo, branch=branch, chronicle_ref=chronicle_ref)
    effect = records.effect_summary(deleted)
    post_gaps = policy.post_effect_gaps(before=before, after=after, deleted=deleted)
    context |= _data(effect=effect, observation=observation.public_observation(after))
    if post_gaps:
        return _blocked(result, post_gaps, **context)
    receipt = records.receipt_payload(
        operation_id=operation_id,
        branch=branch,
        expect_head=expected,
        reason=reason,
        before=before,
        after=after,
        effect=effect,
        chronicle_unchanged=observation.chronicle_binding(before)
        == observation.chronicle_binding(after),
    )
    receipt_path, gap = _write(
        records.receipt_path(records_root, operation_id), receipt, records.RECEIPT_KIND
    )
    if gap:
        return _blocked(result, [gap], **context)
    return (
        result
        | context
        | _data(
            ok=True,
            state="retired_unbound_exceptional",
            receipt_path=receipt_path,
            receipt=receipt,
            required_gaps=[],
            mutation=reporting.mutation(
                branch=branch,
                expect_head=expected,
                reason=reason,
                chronicle_ref=chronicle_ref,
                apply=True,
                confirmed=True,
                observed=after,
                break_glass=break_glass,
                confirm_irreversible=confirm_irreversible,
                gaps=[],
            ),
        )
    )


def _observe(repo: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
    """Keep the local seam for observation-drift contract tests."""
    return observation.observe(repo, branch=branch, chronicle_ref=chronicle_ref)
