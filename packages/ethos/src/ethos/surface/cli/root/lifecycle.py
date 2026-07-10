"""Root land and publish lifecycle commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import cast

from cyclopts import Parameter

import ethos.adapters.repo.git as git
import ethos.domain.land.core as land_core
import ethos.domain.land.publication as land_publication
from ethos.adapters.admission.control_replacement import control_replacement_report
from ethos.adapters.mutation.core import MutationEvaluation
from ethos.adapters.mutation.core import MutationRequest
from ethos.adapters.mutation.core import apply_candidate_to_accepted
from ethos.adapters.mutation.core import apply_land_to_candidate
from ethos.adapters.mutation.core import candidate_base_report
from ethos.adapters.mutation.core import evaluate_closeout_mutation
from ethos.adapters.mutation.core import evaluate_mutation
from ethos.adapters.mutation.core import mutation_envelope
from ethos.adapters.mutation.core import proof_readiness_report
from ethos.adapters.openspec.metadata.core import completed_active_changes_report
from ethos.adapters.repo.status.core import workspace_status
from ethos.repository.context import context_for_root
from ethos.repository.openspec.audit import protected_branch_active_change_required_gaps
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class _CloseoutPayload:
    repo: Path
    mutation: MutationRequest
    decision: MutationEvaluation
    current_head: str
    audit_root: Path
    audit: dict[str, Any]
    lifecycle: dict[str, Any]
    update: dict[str, object]
    gaps: tuple[str, ...]
    ok: bool
    control_replacement: dict[str, object]


@dataclass(frozen=True)
class _PublishOptions:
    """CLI options for `ethos publish`, including legacy hook metadata."""

    legacy_hook_args: Annotated[
        tuple[str, ...],
        Parameter(name="*", show=False),
    ] = ()
    apply: bool = False
    authorize: bool = False
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None


_DEFAULT_PUBLISH_OPTIONS = _PublishOptions()


def _mapping_payload(value: object) -> dict[str, object]:
    """Return a JSON mapping payload, or an empty mapping for malformed data."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}


def _gap_tuple(payload: Mapping[str, object]) -> tuple[str, ...]:
    """Read required gaps from a JSON payload as strings."""
    raw_gaps = payload.get("required_gaps", ())
    if isinstance(raw_gaps, list | tuple):
        return tuple(str(gap) for gap in raw_gaps)
    return ()


def _first_string(value: object) -> str:
    """Return the first string-like item from a JSON list payload."""
    if isinstance(value, list) and value:
        return str(value[0])
    return ""


def _int_value(value: object, *, default: int = 0) -> int:
    """Return an integer from a JSON scalar without trusting arbitrary objects."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _closeout_result(payload: _CloseoutPayload) -> EthosResult:
    mutation_next_actions = land_core.closeout_next_actions(
        ok=payload.ok,
        gaps=payload.gaps,
        current_head=git.current_head(payload.repo),
        state=payload.decision.state,
    )
    return EthosResult(
        command="land",
        ok=payload.ok,
        state=(
            "accepted_current"
            if payload.ok and payload.decision.state == "current"
            else "ready_to_closeout"
            if payload.ok and not payload.mutation.apply
            else "deferred"
            if payload.control_replacement.get("verdict") == "defer"
            else "blocked"
            if payload.gaps
            else str(payload.update.get("state") or payload.mutation.command)
        ),
        required_gaps=payload.gaps,
        next_actions=mutation_next_actions,
        governance_context=context_for_root(payload.audit_root),
        data={
            "repository_audit": payload.audit,
            "openspec_lifecycle": payload.lifecycle,
            "accepted_update": payload.update,
            "control_replacement": payload.control_replacement,
            "closeout_bootstrap": land_core.closeout_bootstrap_package(
                repo=payload.repo,
                audit_root=payload.audit_root,
                required_gaps=payload.gaps,
            ),
            "mutation": mutation_envelope(
                payload.mutation,
                action="accepted.advance",
                resource=f"refs/heads/{load_branch_role_policy(payload.repo).accepted_branch}",
                expected_state=_closeout_expected_state(payload),
                verdict=(
                    "allow"
                    if payload.ok
                    else "defer"
                    if payload.control_replacement.get("verdict") == "defer"
                    else "block"
                ),
                required_gaps=payload.gaps,
                why=("candidate_already_current",)
                if payload.ok and payload.decision.state == "current"
                else (),
                next_actions=mutation_next_actions,
                state=payload.decision.state,
            ),
        },
    )


def _publish_next_actions(*, ok: bool, publication: dict[str, object]) -> tuple[str, ...]:
    """Return top-level publish actions without hiding publication work."""
    if not ok:
        return ("ethos land --json",)

    publication_actions = cast("list[object]", publication.get("next_actions", []))
    actions = [str(action) for action in publication_actions]
    actions.append("ethos report")
    return tuple(dict.fromkeys(actions))


def _land_expected_state(
    *,
    repo: Path,
    current_head: str,
    status_payload: Mapping[str, object],
    closeout_support: Mapping[str, object],
) -> dict[str, object]:
    policy = load_branch_role_policy(repo)
    candidate = _mapping_payload(status_payload.get("candidate", {}))
    return {
        "root": repo.resolve().as_posix(),
        "source_ref": f"refs/heads/{status_payload.get('branch', '')}",
        "source_head": current_head,
        "target_ref": f"refs/heads/{policy.candidate_branch}",
        "target_head": str(candidate.get("head") or ""),
        "holder_ref": str(closeout_support.get("holder_ref") or ""),
        "lease_id": str(closeout_support.get("lease_id") or ""),
        "lease_epoch": _int_value(closeout_support.get("lease_epoch")),
    }


def _closeout_expected_state(payload: _CloseoutPayload) -> dict[str, object]:
    policy = load_branch_role_policy(payload.repo)
    status_payload = workspace_status(payload.repo)
    candidate = _mapping_payload(status_payload.get("candidate", {}))
    return {
        "root": payload.repo.resolve().as_posix(),
        "accepted_ref": f"refs/heads/{policy.accepted_branch}",
        "accepted_head": payload.current_head,
        "candidate_ref": f"refs/heads/{policy.candidate_branch}",
        "candidate_head": str(candidate.get("head") or ""),
    }


def _publish_expected_state(
    *,
    repo: Path,
    branch: str,
    current_head: str,
    publication: Mapping[str, object],
    remote_sync: Mapping[str, object],
    remote_availability: Mapping[str, object],
) -> dict[str, object]:
    submit_branch = str(publication.get("submit_branch") or "")
    target_branch = submit_branch or branch
    remote = str(remote_availability.get("remote") or "origin")
    return {
        "root": repo.resolve().as_posix(),
        "source_ref": f"refs/heads/{branch}",
        "source_head": current_head,
        "remote": remote,
        "target_ref": f"refs/heads/{target_branch}",
        "observed_remote_ref": str(remote_sync.get("remote_ref") or ""),
        "observed_remote_head": str(remote_sync.get("remote_head") or ""),
        "remote_availability_state": str(remote_availability.get("state") or "not_probed"),
        "remote_sync_state": str(remote_sync.get("state") or "not_checked"),
    }


def _validate_legacy_publish_hook_args(args: tuple[str, ...]) -> None:
    """Accept Git pre-push remote metadata from old hook projections only."""
    if len(args) in {0, 2}:
        return
    raise SystemExit(2)


@app.command
def land(
    *,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    closeout: bool = False,
    control_verifier_receipt: Annotated[
        Path | None, Parameter(name="--control-verifier-receipt")
    ] = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report land readiness."""
    repo = resolve_root(root)
    current_head = git.current_head(repo)
    if closeout:
        request = MutationRequest(
            command="closeout",
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
        )
        decision = evaluate_closeout_mutation(
            request,
            root=repo,
            current_head=current_head,
        )
        audit_root = land_core.closeout_audit_root(repo, decision)
        audit = land_core.repository_audit_after_admission(audit_root, decision)
        lifecycle = completed_active_changes_report(audit_root)
        status_payload = workspace_status(repo)
        candidate = _mapping_payload(status_payload.get("candidate", {}))
        control_replacement = control_replacement_report(
            accepted_root=repo,
            candidate_root=audit_root,
            accepted_head=current_head,
            candidate_head=str(candidate.get("head") or current_head),
            external_receipt=control_verifier_receipt,
        )
        control_gaps = _gap_tuple(control_replacement)
        gaps = _gap_tuple(audit) + decision.gaps + _gap_tuple(lifecycle) + control_gaps
        ok = bool(audit["ok"]) and decision.ok and bool(lifecycle["ok"]) and not control_gaps
        update: dict[str, object] = {}
        if ok and apply:
            fresh_status = workspace_status(repo)
            fresh_candidate = _mapping_payload(fresh_status.get("candidate", {}))
            control_replacement = control_replacement_report(
                accepted_root=repo,
                candidate_root=audit_root,
                accepted_head=current_head,
                candidate_head=str(fresh_candidate.get("head") or current_head),
                external_receipt=control_verifier_receipt,
            )
            fresh_control_gaps = _gap_tuple(control_replacement)
            if fresh_control_gaps:
                gaps = gaps + fresh_control_gaps
                ok = False
        if ok and apply:
            update = apply_candidate_to_accepted(
                root=repo,
                authorized=authorize,
                expect_head=expect_head,
            )
            gaps = gaps + _gap_tuple(update)
            ok = bool(update["ok"])
        result = _closeout_result(
            _CloseoutPayload(
                repo=repo,
                mutation=request,
                decision=decision,
                audit_root=audit_root,
                audit=audit,
                lifecycle=lifecycle,
                update=update,
                gaps=gaps,
                ok=ok,
                current_head=current_head,
                control_replacement=control_replacement,
            )
        )
        emit(result, json_output=json_output, enforce=apply)
        return

    governance = context_for_root(repo)
    status_payload = workspace_status(repo)
    closeout_support = _mapping_payload(status_payload.get("closeout_support", {}))
    closeout_gaps: tuple[str, ...] = ()
    if status_payload.get("role") == "work_lane" and not closeout_support.get("supported"):
        closeout_gaps = _gap_tuple(closeout_support)
    request = MutationRequest(
        command="land",
        apply=apply,
        authorized=authorize,
        expect_head=expect_head,
    )
    decision = evaluate_mutation(request, root=repo, current_head=current_head)
    audit = land_core.repository_audit_after_admission(repo, decision)
    lifecycle = completed_active_changes_report(repo)
    gaps = _gap_tuple(audit) + decision.gaps + closeout_gaps + _gap_tuple(lifecycle)
    ok = bool(audit["ok"]) and decision.ok and bool(lifecycle["ok"]) and not closeout_gaps
    update: dict[str, object] = {}
    if ok and apply:
        update = apply_land_to_candidate(
            root=repo,
            authorized=authorize,
            expect_head=expect_head,
            admitted_decision=decision,
        )
        gaps = gaps + _gap_tuple(update)
        ok = bool(update["ok"])
    elif ok:
        update = candidate_base_report(root=repo)
        if not update["ok"]:
            gaps = gaps + _gap_tuple(update)
            ok = False
    proof_readiness: dict[str, object] = {}
    if ok and not apply:
        proof_readiness = proof_readiness_report(repo, current_head)
        gaps = gaps + _gap_tuple(proof_readiness)
        ok = not bool(proof_readiness["blocking"])
    state = (
        "ready_to_land"
        if ok and not apply
        else "blocked"
        if gaps
        else str(update.get("state") or decision.state)
    )
    mutation_next_actions = land_core.land_next_actions(
        ok=ok,
        gaps=gaps,
        current_head=current_head,
    )
    result = EthosResult(
        command="land",
        ok=ok,
        state=state,
        required_gaps=gaps,
        next_actions=mutation_next_actions,
        governance_context=governance,
        data={
            "repository_audit": audit,
            "openspec_lifecycle": lifecycle,
            "candidate_update": update,
            "closeout_support": closeout_support,
            "proof_readiness": proof_readiness,
            "mutation": mutation_envelope(
                request,
                action="candidate.integrate",
                resource=f"refs/heads/{load_branch_role_policy(repo).candidate_branch}",
                expected_state=_land_expected_state(
                    repo=repo,
                    current_head=current_head,
                    status_payload=status_payload,
                    closeout_support=closeout_support,
                ),
                verdict="allow" if ok else "block",
                required_gaps=gaps,
                next_actions=mutation_next_actions,
                state=state,
            ),
        },
    )
    emit(result, json_output=json_output, enforce=apply)


@app.command
def publish(
    options: Annotated[
        _PublishOptions,
        Parameter(name="*"),
    ] = _DEFAULT_PUBLISH_OPTIONS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report publish readiness without pushing."""
    _validate_legacy_publish_hook_args(options.legacy_hook_args)
    repo = resolve_root(root)
    governance = context_for_root(repo)
    current_head = git.current_head(repo)
    decision = evaluate_mutation(
        MutationRequest(
            command="publish",
            apply=options.apply,
            authorized=options.authorize,
            expect_head=options.expect_head,
        ),
        root=repo,
        current_head=current_head,
    )
    audit = land_core.repository_audit_after_admission(repo, decision)
    branch = workspace_status(repo)["branch"]
    release_carrier_gaps = tuple(
        protected_branch_active_change_required_gaps(repo, current_branch=str(branch))
    )
    gaps = _gap_tuple(audit) + decision.gaps + release_carrier_gaps
    ok = bool(audit["ok"]) and decision.ok and not release_carrier_gaps
    remote_sync = git.remote_tracking_sync(repo, str(branch))
    remote_availability = {
        **git.remote_availability(repo),
        "tracking_sync": remote_sync,
    }
    local_ci_fallback = land_publication.local_ci_fallback_package(
        remote_availability=remote_availability,
        root=repo,
        current_head=current_head,
    )
    publication = land_publication.publication_readiness(
        branch=str(branch),
        local_ok=ok,
        policy=load_branch_role_policy(repo),
        remote_availability=remote_availability,
        local_ci_fallback=local_ci_fallback,
    )
    remote_state = str(publication.get("remote_state") or "deferred")
    remote_push = str(publication.get("remote_push") or "not_performed")
    remote_availability_state = str(remote_availability.get("state") or "not_probed")
    publish_summary = {
        "mode": "local_readiness",
        "local_readiness": ok,
        "remote_push": remote_push,
        "remote_publication_state": remote_state,
        "remote_availability_state": remote_availability_state,
        "remote_sync_state": str(remote_sync.get("state") or "not_checked"),
        "remote_ahead": _int_value(remote_sync.get("ahead")),
        "remote_behind": _int_value(remote_sync.get("behind")),
        "hosted_ci_status_claimed": False,
        "submit_branch": str(publication.get("submit_branch") or ""),
        "next_publication_action": _first_string(publication.get("next_actions")),
    }
    publish_next_actions = _publish_next_actions(ok=ok, publication=publication)
    publication_verdict = "block" if gaps else "defer" if remote_state == "deferred" else "allow"
    transition_ok = ok and (not options.apply or publication_verdict == "allow")
    publish_expected_state = _publish_expected_state(
        repo=repo,
        branch=str(branch),
        current_head=current_head,
        publication=publication,
        remote_sync=remote_sync,
        remote_availability=remote_availability,
    )
    result = EthosResult(
        command="publish",
        ok=transition_ok,
        state=(
            "local_publish_ready"
            if ok and not options.apply
            else "publication_deferred"
            if ok and publication_verdict == "defer"
            else "blocked"
            if gaps
            else decision.state
        ),
        summary=publish_summary,
        required_gaps=gaps,
        next_actions=publish_next_actions,
        governance_context=governance,
        data={
            "repository_audit": audit,
            "release_root_open_spec": {
                "required_gaps": list(release_carrier_gaps),
                "blocking": bool(release_carrier_gaps),
            },
            "remote_push": remote_push,
            "remote_availability": remote_availability,
            "remote_sync": remote_sync,
            "local_ci_fallback": local_ci_fallback,
            "publication": publication,
            "mutation": mutation_envelope(
                MutationRequest(
                    command="publish",
                    apply=options.apply,
                    authorized=options.authorize,
                    expect_head=options.expect_head,
                ),
                action="remote.publish",
                resource=str(publish_expected_state["target_ref"]),
                expected_state=publish_expected_state,
                verdict=publication_verdict,
                required_gaps=gaps,
                why=(str(publication.get("remote_state") or "remote_publication_deferred"),),
                next_actions=publish_next_actions,
                state=remote_state,
                evidence_boundary="local_readiness_and_remote_availability",
                enforcement_boundary="remote_ref_transition",
            ),
        },
    )
    emit(result, json_output=json_output, enforce=options.apply)
