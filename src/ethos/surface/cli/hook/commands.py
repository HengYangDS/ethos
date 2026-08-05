"""Hook command group — hook-time write admission and hook installation."""

import json
import pathlib
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Annotated

from cyclopts import Group
from cyclopts import Parameter

from ethos.adapters.admission.git_admission import hook_admission_report
from ethos.adapters.admission.git_admission import push_admission_report
from ethos.adapters.admission.git_admission import ref_move_admission_report
from ethos.adapters.admission.git_admission import resolve_ref_move_policy
from ethos.adapters.admission.identity import ReconciliationObservation
from ethos.adapters.admission.identity import reconciliation_receipt_payload
from ethos.adapters.admission.prewrite import has_invalid_path_token_character
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.repo.config_effects import set_local_config
from ethos.adapters.repo.git import git_stdout
from ethos.contracts.admission import HookAdmissionRequest
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult
from ethos.surface.cli.application import hook_app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

_LANE_PREWRITE_ACTION = "ethos lane prewrite <path>"
_HEAD_BOUND_PROOF_ACTION = "ethos prove --execute --expect-head <head>"
_ADMISSION_OPTIONS = Group("Admission")
_RECONCILIATION_OPTIONS = Group("Reconciliation")


@dataclass(frozen=True, slots=True)
class _HookAdmissionOptions:
    """CLI-only fields for one hook admission request."""

    command: Annotated[str, Parameter(name="--command", group=_ADMISSION_OPTIONS)] = ""
    editor_root: Annotated[
        pathlib.Path | None, Parameter(name="--editor-root", group=_ADMISSION_OPTIONS)
    ] = None
    expected_root: Annotated[
        pathlib.Path | None, Parameter(name="--expected-root", group=_ADMISSION_OPTIONS)
    ] = None
    require_editor_root: Annotated[bool, Parameter(group=_ADMISSION_OPTIONS)] = False
    root: RootOption | None = None
    json_output: JsonFlag = False


@dataclass(frozen=True, slots=True)
class PushReconciliationOptions:
    """CLI-only fields for one hook push reconciliation observation."""

    remote_head: Annotated[str, Parameter(name="--remote-head", group=_RECONCILIATION_OPTIONS)] = ""
    remote: Annotated[str, Parameter(name="--remote", group=_RECONCILIATION_OPTIONS)] = "origin"
    reconciliation_receipt_path: Annotated[
        str, Parameter(name="--reconciliation-receipt", group=_RECONCILIATION_OPTIONS)
    ] = ""
    observed_origin_head: Annotated[
        str, Parameter(name="--observed-origin-head", group=_RECONCILIATION_OPTIONS)
    ] = ""
    observed_origin_main_head: Annotated[
        str, Parameter(name="--observed-origin-main-head", group=_RECONCILIATION_OPTIONS)
    ] = ""
    observed_github_head: Annotated[
        str, Parameter(name="--observed-github-head", group=_RECONCILIATION_OPTIONS)
    ] = ""
    observed_github_main_head: Annotated[
        str, Parameter(name="--observed-github-main-head", group=_RECONCILIATION_OPTIONS)
    ] = ""
    root: RootOption | None = None
    json_output: JsonFlag = False


_DEFAULT_HOOK_ADMISSION_OPTIONS = _HookAdmissionOptions()
_DEFAULT_PUSH_RECONCILIATION_OPTIONS = PushReconciliationOptions(remote_head="")


def _report_result(
    command: str,
    report: dict[str, object],
    summary: dict[str, object],
    next_action_for: Callable[[Verdict], str],
) -> EthosResult:
    verdict = report_verdict(report)
    required_gaps = tuple(string_sequence(report.get("required_gaps")))
    next_action = next_action_for(verdict)
    return EthosResult(
        command=command,
        verdict=verdict,
        state=str(report["state"]),
        summary=summary,
        required_gaps=required_gaps,
        next_action=next_action,
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
    options: Annotated[_HookAdmissionOptions, Parameter(name="*")] = (
        _DEFAULT_HOOK_ADMISSION_OPTIONS
    ),
) -> None:
    """Evaluate hook-time write admission before a host mutates tracked files."""
    repo = resolve_root(options.root)
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
            editor_root=options.editor_root.as_posix() if options.editor_root else None,
            expected_root=options.expected_root.as_posix() if options.expected_root else None,
            require_editor_root=options.require_editor_root,
            command=options.command,
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
        lambda verdict: _hook_admit_next_action(report, verdict),
    )
    emit(result, json_output=options.json_output, enforce=True)


def _hook_admit_next_action(report: dict[str, object], verdict: Verdict) -> str:
    if verdict == "pass":
        return ""
    return str(report.get("next_action") or _LANE_PREWRITE_ACTION)


@hook_app.command
def pre_push(
    target_ref: str,
    pushed_head: str,
    *,
    options: Annotated[PushReconciliationOptions, Parameter(name="*")] = (
        _DEFAULT_PUSH_RECONCILIATION_OPTIONS
    ),
) -> None:
    """Evaluate push admission before a ref is pushed to a protected role.

    Pushing to an accepted/candidate ref requires an executed proof bound to the
    pushed HEAD — the same precondition `land` enforces, now bound to the push tail so
    a raw `git push` cannot move a protected ref unproven. Called by .githooks/pre-push.
    """
    repo = resolve_root(options.root)
    reconciliation = ReconciliationObservation(
        receipt_path=options.reconciliation_receipt_path,
        origin_head=options.observed_origin_head,
        origin_main_head=options.observed_origin_main_head,
        github_head=options.observed_github_head,
        github_main_head=options.observed_github_main_head,
    )
    admission = partial(
        push_admission_report,
        root=repo,
        target_ref=target_ref,
        pushed_head=pushed_head,
        remote_head=options.remote_head,
        remote_name=options.remote,
        reconciliation=reconciliation,
    )
    report = admission()
    result = _report_result(
        "hook pre-push",
        report,
        {
            "target_branch": report["target_branch"],
            "role": report["role"],
            "remote": str(report.get("remote_name", options.remote)),
            "decision": _decision_action(report),
        },
        lambda verdict: _HEAD_BOUND_PROOF_ACTION if verdict != "pass" else "",
    )
    emit(result, json_output=options.json_output, enforce=True)


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
        remote: git_stdout(repo, "rev-parse", "--verify", remote)
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
        verdict="block" if gaps else "pass",
        state="observed" if not gaps else "blocked",
        summary={"proposal_branch": proposal_branch, "source_head": source_head},
        required_gaps=gaps,
        next_action="",
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
    branch = ref_name.removeprefix("refs/heads/")
    try:
        policy = resolve_ref_move_policy(repo, ref_name, old_value, new_value)
    except (TypeError, ValueError):
        report: dict[str, object] = {
            "verdict": "block",
            "state": "blocked",
            "phase": phase,
            "hook": "reference-transaction",
            "ref": ref_name,
            "branch": branch,
            "old_value": old_value,
            "new_value": new_value,
            "decision": {"action": "block", "reason": "ref_move_policy_unavailable"},
            "required_gaps": ["ref_move_policy_unavailable"],
        }
    else:
        report = (
            work_lane_ref_transition_report(
                root=repo,
                phase=phase,
                ref_name=ref_name,
                old_value=old_value,
                new_value=new_value,
            )
            if policy.role_for_branch(branch) == "work_lane"
            else ref_move_admission_report(
                root=repo,
                ref_name=ref_name,
                old_value=old_value,
                new_value=new_value,
                phase=phase,
            )
        )
    result = _report_result(
        "hook ref-transaction",
        report,
        {"branch": report["branch"], "decision": _decision_action(report)},
        lambda verdict: "ethos land --closeout" if verdict != "pass" else "",
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
    attestation = None
    if not gaps:
        try:
            attestation = set_local_config(
                repo, {"core.hooksPath": ".githooks", "gc.packRefs": "false"}
            )
        except ValueError as error:
            gaps.append(f"hook_config_write_failed:{error}")
    wired = attestation is not None
    result = EthosResult(
        command="hook install",
        verdict="block" if gaps else "pass",
        state="installed" if not gaps else "blocked",
        summary={
            "hooks_path": ".githooks",
            "wired": wired,
            "pack_refs_disabled": wired,
        },
        required_gaps=tuple(gaps),
        next_action=(
            "git commit — the pre-commit + pre-push admission gates are now active"
            if not gaps
            else ""
        ),
        data={
            "hooks_path": ".githooks",
            "hook_scripts": list(scripts[:2]),
            "wired": wired,
            "pack_refs_disabled": wired,
            "attestation": attestation.model_dump(mode="json") if attestation else {},
        },
    )
    emit(result, json_output=json_output, enforce=True)
