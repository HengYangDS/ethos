"""Hook command group — hook-time write admission and hook installation."""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures
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


@hook_app.command
def admit(
    layer: str,
    paths: Annotated[tuple[Path, ...], Parameter(consume_multiple=True)] = (),
    *,
    command: Annotated[str, Parameter(name="--command")] = "",
    editor_root: Annotated[Path | None, Parameter(name="--editor-root")] = None,
    expected_root: Annotated[Path | None, Parameter(name="--expected-root")] = None,
    require_editor_root: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Evaluate hook-time write admission before a host mutates tracked files."""
    repo = resolve_root(root)
    report = hook_admission_report(
        HookAdmissionRequest(
            root=repo,
            layer=layer,
            paths=tuple(
                path
                if path.is_absolute() or has_invalid_path_token_character(path.as_posix())
                else repo / path
                for path in paths
            ),
            editor_root=editor_root,
            expected_root=expected_root,
            require_editor_root=require_editor_root,
            command=command,
        )
    )
    decision = report.get("decision", {})
    decision_action = ""
    if isinstance(decision, dict):
        decision_action = str(decision.get("action", ""))
    result = EthosResult(
        command="hook admit",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "layer": report["layer"],
            "role": report["role"],
            "decision": decision_action,
        },
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=_hook_admit_next_actions(report),
        data=report,
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
    report = push_admission_report(
        root=repo,
        target_ref=target_ref,
        pushed_head=pushed_head,
        remote_head=remote_head,
        remote_name=remote,
        reconciliation=reconciliation,
    )
    campaign_publication: dict[str, object] = {}
    if report["ok"]:
        campaign_publication = campaign_publication_report(repo)
        report = push_admission_report(
            root=repo,
            target_ref=target_ref,
            pushed_head=pushed_head,
            remote_head=remote_head,
            remote_name=remote,
            reconciliation=reconciliation,
            campaign_publication=campaign_publication,
        )
    decision = report.get("decision", {})
    decision_action = decision.get("action", "") if isinstance(decision, dict) else ""
    result = EthosResult(
        command="hook pre-push",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "target_branch": report["target_branch"],
            "role": report["role"],
            "remote": str(report.get("remote_name", remote)),
            "decision": decision_action,
            "campaign_publication": campaign_publication.get(
                "remote_publication_admission", "not_evaluated"
            ),
        },
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=_ACTIONS["head_bound_proof"] if not report["ok"] else (),
        data=report,
    )
    emit(result, json_output=json_output, enforce=True)


@hook_app.command(name="reconciliation-receipt")
def reconciliation_receipt_command(
    submit_branch: str,
    source_head: str,
    write_receipt: Annotated[Path, Parameter(name="--write-receipt")],
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Record exact local observations before a one-shot dual-remote submit push."""
    repo = resolve_root(root)
    target = write_receipt.expanduser().resolve()
    if target.is_relative_to(repo):
        error = "reconciliation receipt must be outside the repository root"
        raise ValueError(error)
    origin_head = git_adapter.git_stdout(repo, "rev-parse", "--verify", "origin/dev")
    origin_main_head = git_adapter.git_stdout(repo, "rev-parse", "--verify", "origin/main")
    github_head = git_adapter.git_stdout(repo, "rev-parse", "--verify", "github/dev")
    github_main_head = git_adapter.git_stdout(repo, "rev-parse", "--verify", "github/main")
    gaps = tuple(
        gap
        for gap, head in (
            ("reconciliation_origin_tracking_missing", origin_head),
            ("reconciliation_origin_main_tracking_missing", origin_main_head),
            ("reconciliation_github_tracking_missing", github_head),
            ("reconciliation_github_main_tracking_missing", github_main_head),
        )
        if not head
    )
    receipt = reconciliation_receipt_payload(
        submit_branch=submit_branch,
        source_head=source_head,
        origin_head=origin_head,
        github_head=github_head,
        main_heads=(origin_main_head, github_main_head),
    )
    if not gaps:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = EthosResult(
        command="hook reconciliation-receipt",
        ok=not gaps,
        state="observed" if not gaps else "blocked",
        summary={"submit_branch": submit_branch, "source_head": source_head},
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
    decision = report.get("decision", {})
    decision_action = decision.get("action", "") if isinstance(decision, dict) else ""
    result = EthosResult(
        command="hook ref-transaction",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={"branch": report["branch"], "decision": decision_action},
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=(("ethos land --closeout",) if not report["ok"] else ()),
        data=report,
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
    hook_path = repo / ".githooks" / "pre-commit"
    push_hook_path = repo / ".githooks" / "pre-push"
    ref_hook_path = repo / ".githooks" / "reference-transaction"
    gaps: list[str] = []
    if not hook_path.exists():
        gaps.append("hook_script_missing:.githooks/pre-commit")
    if not push_hook_path.exists():
        gaps.append("hook_script_missing:.githooks/pre-push")
    if not ref_hook_path.exists():
        gaps.append("hook_script_missing:.githooks/reference-transaction")
    wired = git_adapter.set_hooks_path(repo, ".githooks") if not gaps else False
    accepted_branch_recorded = False
    pack_refs_disabled = False
    if not gaps and not wired:
        gaps.append("hooks_path_wire_failed")
    if wired:
        # Record the accepted branch so the reference-transaction hook knows which ref
        # to fail-closed on (the hook runs as a plain shell script with no ETHOS import).
        accepted = load_branch_role_policy(repo).accepted_branch
        accepted_branch_recorded = git_adapter.set_config(repo, "ethos.acceptedBranch", accepted)
        # Git's files ref backend represents `pack-refs` as raw create/delete
        # transactions that a fail-closed accepted-ref hook cannot safely distinguish
        # from semantic mutations. Keep automatic maintenance away from that ambiguous
        # path instead of adding an environment or representation-based bypass.
        pack_refs_disabled = git_adapter.set_config(repo, "gc.packRefs", "false")
        if not accepted_branch_recorded:
            gaps.append("hook_config_write_failed:ethos.acceptedBranch")
        if not pack_refs_disabled:
            gaps.append("hook_config_write_failed:gc.packRefs")
    result = EthosResult(
        command="hook install",
        ok=not gaps,
        state="installed" if not gaps else "blocked",
        summary={
            "hooks_path": ".githooks",
            "wired": wired,
            "pack_refs_disabled": pack_refs_disabled,
        },
        required_gaps=tuple(gaps),
        next_actions=(
            ("git commit — the pre-commit + pre-push admission gates are now active",)
            if not gaps
            else ()
        ),
        data={
            "hooks_path": ".githooks",
            "hook_scripts": [".githooks/pre-commit", ".githooks/pre-push"],
            "wired": wired,
            "accepted_branch_recorded": accepted_branch_recorded,
            "pack_refs_disabled": pack_refs_disabled,
        },
    )
    emit(result, json_output=json_output, enforce=True)
