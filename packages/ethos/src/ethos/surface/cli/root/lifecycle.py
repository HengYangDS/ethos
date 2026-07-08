"""Root land and publish lifecycle commands."""

from __future__ import annotations

import ethos.adapters.repo.git as git
import ethos.domain.land as land_domain
from ethos.adapters.mutation.core import MutationRequest
from ethos.adapters.mutation.core import apply_candidate_to_accepted
from ethos.adapters.mutation.core import apply_land_to_candidate
from ethos.adapters.mutation.core import candidate_base_report
from ethos.adapters.mutation.core import evaluate_closeout_mutation
from ethos.adapters.mutation.core import evaluate_mutation
from ethos.adapters.openspec.metadata.core import completed_active_changes_report
from ethos.adapters.repo.status import workspace_status
from ethos.repository.audit_openspec import protected_branch_active_change_required_gaps
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.branch_roles import load_branch_role_policy
from ethos_core.result import EthosResult


def _closeout_result(repo, mutation, decision, audit_root, audit, lifecycle, update, gaps, ok):
    return EthosResult(
        command="land",
        ok=ok,
        state=(
            "ready_to_closeout"
            if ok and not mutation.apply
            else "blocked"
            if gaps
            else str(update.get("state") or mutation.command)
        ),
        required_gaps=gaps,
        next_actions=land_domain.closeout_next_actions(
            ok=ok, gaps=gaps, current_head=git.current_head(repo)
        ),
        data={
            "repository_audit": audit,
            "openspec_lifecycle": lifecycle,
            "accepted_update": update,
            "closeout_bootstrap": land_domain.closeout_bootstrap_package(
                repo=repo,
                audit_root=audit_root,
                required_gaps=gaps,
            ),
            "mutation": {
                "apply": mutation.apply,
                "authorized": mutation.authorized,
                "expect_head": mutation.expect_head,
                "current_head": git.current_head(repo),
                "decision": decision.state,
                "closeout": True,
            },
        },
    )


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
            repo, request, decision, audit_root, audit, lifecycle, update, gaps, ok
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
            ok=ok, gaps=gaps, current_head=git.current_head(repo)
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
    result = EthosResult(
        command="publish",
        ok=ok,
        state=("ready_to_publish" if ok and not apply else "blocked" if gaps else decision.state),
        required_gaps=gaps,
        next_actions=("ethos report",) if ok else ("ethos land --json",),
        data={
            "repository_audit": audit,
            "release_root_open_spec": {
                "required_gaps": list(release_carrier_gaps),
                "blocking": bool(release_carrier_gaps),
            },
            "remote_push": "not_performed",
            "remote_availability": remote_availability,
            "local_ci_fallback": land_domain.local_ci_fallback_package(
                remote_availability=remote_availability,
            ),
            "publication": land_domain.publication_readiness(
                branch=str(branch),
                local_ok=ok,
                policy=load_branch_role_policy(repo),
                remote_availability=remote_availability,
            ),
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
