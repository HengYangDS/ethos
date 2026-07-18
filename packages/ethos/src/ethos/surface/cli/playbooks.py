"""Playbooks command group — skills-registry check and intent routing."""

from __future__ import annotations

from ethos.adapters.repo.dirty.core import change_scope_paths_from_status
from ethos.adapters.repo.status.core import workspace_status
from ethos.assistants.playbooks import playbooks_report
from ethos.assistants.playbooks import route_playbook
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import playbooks_app
from ethos.surface.cli._base import resolve_root
from ethos_core.normalization.core import string_sequence
from ethos_core.result import EthosResult


@playbooks_app.command(name="check")
def playbooks_check(
    *,
    root: RootOption | None = None,
    mode: str = "v2-strict",
    json_output: JsonFlag = False,
) -> None:
    """Check repo-local ETHOS playbook projection."""
    repo = resolve_root(root)
    report = playbooks_report(repo, mode=mode)
    result = EthosResult(
        command="playbooks check",
        ok=bool(report["ok"]),
        state="ready" if report["ok"] else "gapped",
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=("ethos playbooks route",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@playbooks_app.command(name="route")
def playbooks_route(
    *,
    subject: str = "repository-governance",
    changed: bool = False,
    root: RootOption | None = None,
    mode: str = "v2-strict",
    json_output: JsonFlag = False,
) -> None:
    """Route a subject to repo-local ETHOS playbooks."""
    repo = resolve_root(root)
    route_subject = "changed-scope" if changed else subject
    status_payload = workspace_status(repo, include_foreign_path_scope=False)
    changed_paths = change_scope_paths_from_status(repo, status_payload) if changed else ()
    report = route_playbook(
        repo,
        route_subject,
        require_explicit_subject=changed,
        mode=mode,
        changed_paths=changed_paths,
    )
    result = EthosResult(
        command="playbooks route",
        ok=bool(report["ok"]),
        state="routed" if report["ok"] else "gapped",
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)
