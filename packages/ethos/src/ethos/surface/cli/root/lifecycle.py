"""Root land and publish lifecycle commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import ethos.adapters.repo.git as git
import ethos.domain.land as land_domain
from ethos.adapters.mutation.core import MutationRequest
from ethos.adapters.mutation.core import apply_candidate_to_accepted
from ethos.adapters.mutation.core import apply_land_to_candidate
from ethos.adapters.mutation.core import candidate_base_report
from ethos.adapters.mutation.core import evaluate_closeout_mutation
from ethos.adapters.mutation.core import evaluate_mutation
from ethos.adapters.openspec.metadata.core import completed_active_changes_report
from ethos.adapters.repo.status.core import workspace_status
from ethos.repository.audit_openspec import protected_branch_active_change_required_gaps
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.branch_roles import load_branch_role_policy
from ethos_core.result import EthosResult

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class _CloseoutPayload:
    repo: Path
    mutation: MutationRequest
    decision: object
    audit_root: Path
    audit: dict[str, Any]
    lifecycle: dict[str, Any]
    update: dict[str, object]
    gaps: tuple[str, ...]
    ok: bool


def _closeout_result(payload: _CloseoutPayload) -> EthosResult:
    return EthosResult(
        command="land",
        ok=payload.ok,
        state=(
            "ready_to_closeout"
            if payload.ok and not payload.mutation.apply
            else "blocked"
            if payload.gaps
            else str(payload.update.get("state") or payload.mutation.command)
        ),
        required_gaps=payload.gaps,
        next_actions=land_domain.closeout_next_actions(
            ok=payload.ok, gaps=payload.gaps, current_head=git.current_head(payload.repo)
        ),
        data={
            "repository_audit": payload.audit,
            "openspec_lifecycle": payload.lifecycle,
            "accepted_update": payload.update,
            "closeout_bootstrap": land_domain.closeout_bootstrap_package(
                repo=payload.repo,
                audit_root=payload.audit_root,
                required_gaps=payload.gaps,
            ),
            "mutation": {
                "apply": payload.mutation.apply,
                "authorized": payload.mutation.authorized,
                "expect_head": payload.mutation.expect_head,
                "current_head": git.current_head(payload.repo),
                "decision": payload.decision.state,
                "closeout": True,
            },
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


@app.command
def land(
    *,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    closeout: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report land readiness."""
    repo = resolve_root(root)
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
            current_head=git.current_head(repo),
        )
        audit_root = land_domain.closeout_audit_root(repo, decision)
        audit = land_domain.repository_audit_after_admission(audit_root, decision)
        lifecycle = completed_active_changes_report(audit_root)
        gaps = tuple(audit["required_gaps"]) + decision.gaps + tuple(lifecycle["required_gaps"])
        ok = bool(audit["ok"]) and decision.ok and bool(lifecycle["ok"])
        update: dict[str, object] = {}
        if ok and apply:
            update = apply_candidate_to_accepted(
                root=repo,
                authorized=authorize,
                expect_head=expect_head,
            )
            gaps = gaps + tuple(update["required_gaps"])
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
            )
        )
        emit(result, json_output=json_output, enforce=apply)
        return

    status_payload = workspace_status(repo)
    closeout_support = dict(status_payload.get("closeout_support", {}))
    closeout_gaps: tuple[str, ...] = ()
    if status_payload.get("role") == "work_lane" and not closeout_support.get("supported"):
        closeout_gaps = tuple(str(gap) for gap in closeout_support.get("required_gaps", ()))
    request = MutationRequest(
        command="land",
        apply=apply,
        authorized=authorize,
        expect_head=expect_head,
    )
    decision = evaluate_mutation(request, root=repo, current_head=git.current_head(repo))
    audit = land_domain.repository_audit_after_admission(repo, decision)
    lifecycle = completed_active_changes_report(repo)
    gaps = (
        tuple(audit["required_gaps"])
        + decision.gaps
        + closeout_gaps
        + tuple(lifecycle["required_gaps"])
    )
    ok = bool(audit["ok"]) and decision.ok and bool(lifecycle["ok"]) and not closeout_gaps
    update: dict[str, object] = {}
    if ok and apply:
        update = apply_land_to_candidate(
            root=repo,
            authorized=authorize,
            expect_head=expect_head,
            admitted_decision=decision,
        )
        gaps = gaps + tuple(update["required_gaps"])
        ok = bool(update["ok"])
    elif ok:
        update = candidate_base_report(root=repo)
        if not update["ok"]:
            gaps = gaps + tuple(update["required_gaps"])
            ok = False
    state = (
        "ready_to_land"
        if ok and not apply
        else "blocked"
        if gaps
        else str(update.get("state") or decision.state)
    )
    result = EthosResult(
        command="land",
        ok=ok,
        state=state,
        required_gaps=gaps,
        next_actions=land_domain.land_next_actions(
            ok=ok,
            gaps=gaps,
            current_head=git.current_head(repo),
        ),
        data={
            "repository_audit": audit,
            "openspec_lifecycle": lifecycle,
            "candidate_update": update,
            "closeout_support": closeout_support,
            "mutation": {
                "apply": apply,
                "authorized": authorize,
                "expect_head": expect_head,
                "current_head": git.current_head(repo),
                "decision": decision.state,
            },
        },
    )
    emit(result, json_output=json_output, enforce=apply)


@app.command
def publish(
    *,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report publish readiness without pushing."""
    repo = resolve_root(root)
    decision = evaluate_mutation(
        MutationRequest(
            command="publish",
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
        ),
        root=repo,
        current_head=git.current_head(repo),
    )
    audit = land_domain.repository_audit_after_admission(repo, decision)
    branch = workspace_status(repo)["branch"]
    release_carrier_gaps = tuple(
        protected_branch_active_change_required_gaps(repo, current_branch=str(branch))
    )
    gaps = tuple(audit["required_gaps"]) + decision.gaps + release_carrier_gaps
    ok = bool(audit["ok"]) and decision.ok and not release_carrier_gaps
    remote_availability = git.remote_availability(repo)
    local_ci_fallback = land_domain.local_ci_fallback_package(
        remote_availability=remote_availability,
    )
    publication = land_domain.publication_readiness(
        branch=str(branch),
        local_ok=ok,
        policy=load_branch_role_policy(repo),
        remote_availability=remote_availability,
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
        "hosted_ci_status_claimed": False,
        "submit_branch": str(publication.get("submit_branch") or ""),
        "next_publication_action": str(
            (publication.get("next_actions") or [""])[0]
            if isinstance(publication.get("next_actions"), list)
            else ""
        ),
    }
    result = EthosResult(
        command="publish",
        ok=ok,
        state=("ready_to_publish" if ok and not apply else "blocked" if gaps else decision.state),
        summary=publish_summary,
        required_gaps=gaps,
        next_actions=_publish_next_actions(ok=ok, publication=publication),
        data={
            "repository_audit": audit,
            "release_root_open_spec": {
                "required_gaps": list(release_carrier_gaps),
                "blocking": bool(release_carrier_gaps),
            },
            "remote_push": remote_push,
            "remote_availability": remote_availability,
            "local_ci_fallback": local_ci_fallback,
            "publication": publication,
            "mutation": {
                "apply": apply,
                "authorized": authorize,
                "expect_head": expect_head,
                "current_head": git.current_head(repo),
                "decision": decision.state,
            },
        },
    )
    emit(result, json_output=json_output, enforce=apply)
