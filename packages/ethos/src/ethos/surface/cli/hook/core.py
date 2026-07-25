"""Hook command group — hook-time write admission and hook installation."""

from __future__ import annotations

import json
import pathlib  # noqa: TC003 - Cyclopts resolves these runtime annotations.
from functools import partial
from typing import Annotated
from typing import cast

from cyclopts import Parameter

import ethos.adapters.repo.git as git_adapter
from ethos.adapters.admission.core import hook_admission_report
from ethos.adapters.admission.core import push_admission_report
from ethos.adapters.admission.core import ref_move_admission_report
from ethos.adapters.admission.identity import ReconciliationObservation
from ethos.adapters.admission.identity import reconciliation_receipt_payload
from ethos.adapters.admission.prewrite import has_invalid_path_token_character
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.domain.campaign.closeout import campaign_publication_report
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import hook_app
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.admission import HookAdmissionRequest
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.contracts.commands import load_command_registry_declaration
from ethos_core.normalization.core import string_sequence
from ethos_core.result import EthosResult

_ACTIONS = load_command_registry_declaration().actions


def _report_result(
    command: str,
    report: dict[str, object],
    summary: dict[str, object],
    next_actions: tuple[str, ...],
) -> EthosResult:
    return EthosResult(
        command=command,
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=summary,
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=next_actions,
        data=report,
    )


def _decision_action(report: dict[str, object]) -> str:
    decision = report.get("decision")
    return str(decision.get("action") or "") if isinstance(decision, dict) else ""


@hook_app.command
def admit(
    layer: str,
    paths: Annotated[tuple[pathlib.Path, ...], Parameter(consume_multiple=True)] = (),
    *,
    command: Annotated[str, Parameter(name="--command")] = "",
    editor_root: Annotated[pathlib.Path | None, Parameter(name="--editor-root")] = None,
    expected_root: Annotated[pathlib.Path | None, Parameter(name="--expected-root")] = None,
    require_editor_root: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Evaluate hook-time write admission before a host mutates tracked files."""
    repo = resolve_root(root)
    report = hook_admission_report(
        request=HookAdmissionRequest(
            root=repo.as_posix(),
            layer=layer,
            paths=tuple(
                (
                    path
                    if path.is_absolute() or has_invalid_path_token_character(path.as_posix())
                    else repo / path
                ).as_posix()
                for path in paths
            ),
            editor_root=editor_root.as_posix() if editor_root else None,
            expected_root=expected_root.as_posix() if expected_root else None,
            require_editor_root=require_editor_root,
            command=command,
        )
    )
    result = _report_result(
        "hook admit",
        report,
        {
            "layer": report["layer"],
            "role": report["role"],
            "decision": _decision_action(report),
        },
        _hook_admit_next_actions(report),
    )
    emit(result, json_output=json_output, enforce=True)


def _hook_admit_next_actions(report: dict[str, object]) -> tuple[str, ...]:
    if report["ok"] is True:
        return ()
    actions = report.get("next_actions")
    if isinstance(actions, list):
        return tuple(str(action) for action in cast("list[object]", actions))
    return _ACTIONS["lane_prewrite"]


@hook_app.command
def pre_push(
    target_ref: str,
    pushed_head: str,
    *,
    remote_head: Annotated[str, Parameter(name="--remote-head")] = "",
    remote: Annotated[str, Parameter(name="--remote")] = "origin",
    reconciliation_receipt_path: Annotated[str, Parameter(name="--reconciliation-receipt")] = "",
    observed_origin_head: Annotated[str, Parameter(name="--observed-origin-head")] = "",
    observed_origin_main_head: Annotated[str, Parameter(name="--observed-origin-main-head")] = "",
    observed_github_head: Annotated[str, Parameter(name="--observed-github-head")] = "",
    observed_github_main_head: Annotated[str, Parameter(name="--observed-github-main-head")] = "",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Evaluate push admission before a ref is pushed to a protected role.

    Pushing to an accepted/candidate ref requires an executed proof bound to the
    pushed HEAD — the same precondition `land` enforces, now bound to the push tail so
    a raw `git push` cannot move a protected ref unproven. Called by .githooks/pre-push.
    """
    repo = resolve_root(root)
    reconciliation = ReconciliationObservation(
        receipt_path=reconciliation_receipt_path,
        origin_head=observed_origin_head,
        origin_main_head=observed_origin_main_head,
        github_head=observed_github_head,
        github_main_head=observed_github_main_head,
    )
    admission = partial(
        push_admission_report,
        root=repo,
        target_ref=target_ref,
        pushed_head=pushed_head,
        remote_head=remote_head,
        remote_name=remote,
        reconciliation=reconciliation,
    )
    report = admission()
    campaign_publication: dict[str, object] = {}
    if report["ok"]:
        campaign_publication = campaign_publication_report(repo)
        report = admission(campaign_publication=campaign_publication)
    result = _report_result(
        "hook pre-push",
        report,
        {
            "target_branch": report["target_branch"],
            "role": report["role"],
            "remote": str(report.get("remote_name", remote)),
            "decision": _decision_action(report),
            "campaign_publication": campaign_publication.get(
                "remote_publication_admission", "not_evaluated"
            ),
        },
        _ACTIONS["head_bound_proof"] if not report["ok"] else (),
    )
    emit(result, json_output=json_output, enforce=True)


@hook_app.command(name="reconciliation-receipt")
def reconciliation_receipt_command(
    proposal_branch: str,
    source_head: str,
    write_receipt: Annotated[pathlib.Path, Parameter(name="--write-receipt")],
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Record exact local observations before a one-shot dual-remote proposal push."""
    repo = resolve_root(root)
    target = write_receipt.expanduser().resolve()
    if target.is_relative_to(repo):
        error = "reconciliation receipt must be outside the repository root"
        raise ValueError(error)
    refs = {
        remote: git_adapter.git_stdout(repo, "rev-parse", "--verify", remote)
        for remote in ("origin/dev", "origin/main", "github/dev", "github/main")
    }
    gaps = tuple(
        gap
        for remote, gap in (
            ("origin/dev", "reconciliation_origin_tracking_missing"),
            ("origin/main", "reconciliation_origin_main_tracking_missing"),
            ("github/dev", "reconciliation_github_tracking_missing"),
            ("github/main", "reconciliation_github_main_tracking_missing"),
        )
        if not refs[remote]
    )
    receipt = reconciliation_receipt_payload(
        proposal_branch=proposal_branch,
        source_head=source_head,
        origin_head=refs["origin/dev"],
        github_head=refs["github/dev"],
        main_heads=(refs["origin/main"], refs["github/main"]),
    )
    if not gaps:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = EthosResult(
        command="hook reconciliation-receipt",
        ok=not gaps,
        state="observed" if not gaps else "blocked",
        summary={"proposal_branch": proposal_branch, "source_head": source_head},
        required_gaps=gaps,
        next_actions=(),
        data={"receipt": receipt, "path": str(target)},
    )
    emit(result, json_output=json_output, enforce=True)


@hook_app.command
def ref_transaction(
    ref_name: str,
    old_value: str,
    new_value: str,
    *,
    phase: str = "prepared",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Evaluate a LOCAL ref update before it is committed to the ref store.

    Bound to git's reference-transaction hook, this closes the candidate-train bypass:
    a raw `git merge --ff-only work/x dev` (or `git branch -f`/`reset`) can move the
    accepted branch directly, skipping candidate validation. This blocks any accepted-
    branch advance that is not both candidate-contained and proof-bound, so the
    two-stage land->closeout path is the only reachable way to advance dev.
    """
    repo = resolve_root(root)
    policy = load_branch_role_policy(repo)
    branch = ref_name.removeprefix("refs/heads/")
    report = (
        work_lane_ref_transition_report(
            root=repo,
            phase=phase,
            ref_name=ref_name,
            old_value=old_value,
            new_value=new_value,
        )
        if policy.role_for_branch(branch) == "work_lane"
        else {
            "ok": True,
            "state": "admitted",
            "phase": phase,
            "ref": ref_name,
            "branch": branch,
            "old_value": old_value,
            "new_value": new_value,
            "decision": {"action": "allow", "reason": "ref_move_committed"},
            "required_gaps": [],
        }
        if phase == "committed"
        else ref_move_admission_report(
            root=repo, ref_name=ref_name, old_value=old_value, new_value=new_value
        )
    )
    result = _report_result(
        "hook ref-transaction",
        report,
        {"branch": report["branch"], "decision": _decision_action(report)},
        ("ethos land --closeout",) if not report["ok"] else (),
    )
    emit(result, json_output=json_output, enforce=True)


@hook_app.command
def install(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Install the write-admission git hooks by wiring core.hooksPath to .githooks."""
    repo = resolve_root(root)
    scripts = (
        ".githooks/pre-commit",
        ".githooks/pre-push",
        ".githooks/reference-transaction",
    )
    gaps: list[str] = [
        f"hook_script_missing:{path}" for path in scripts if not (repo / path).exists()
    ]
    wired = git_adapter.set_hooks_path(repo, ".githooks") if not gaps else False
    if not gaps and not wired:
        gaps.append("hooks_path_wire_failed")
    configured = {
        "ethos.acceptedBranch": wired
        and git_adapter.set_config(
            repo, "ethos.acceptedBranch", load_branch_role_policy(repo).accepted_branch
        ),
        "gc.packRefs": wired and git_adapter.set_config(repo, "gc.packRefs", "false"),
    }
    for key, ok in configured.items():
        if wired and not ok:
            gaps.append(f"hook_config_write_failed:{key}")
    result = EthosResult(
        command="hook install",
        ok=not gaps,
        state="installed" if not gaps else "blocked",
        summary={
            "hooks_path": ".githooks",
            "wired": wired,
            "pack_refs_disabled": configured["gc.packRefs"],
        },
        required_gaps=tuple(gaps),
        next_actions=(
            ("git commit — the pre-commit + pre-push admission gates are now active",)
            if not gaps
            else ()
        ),
        data={
            "hooks_path": ".githooks",
            "hook_scripts": list(scripts[:2]),
            "wired": wired,
            "accepted_branch_recorded": configured["ethos.acceptedBranch"],
            "pack_refs_disabled": configured["gc.packRefs"],
        },
    )
    emit(result, json_output=json_output, enforce=True)
