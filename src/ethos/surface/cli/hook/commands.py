"""Hook command group — hook-time write admission and hook installation."""

import pathlib
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from cyclopts import App
from cyclopts import Group
from cyclopts import Parameter

from ethos.adapters.admission.git_admission import hook_admission_report
from ethos.adapters.admission.git_admission import push_admission_report
from ethos.adapters.admission.git_admission import ref_move_admission_report
from ethos.adapters.admission.prewrite import has_invalid_path_token_character
from ethos.adapters.admission.ref_move_policy import resolve_ref_move_policy
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.repo.hook_runtime import execute_hook
from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.contracts.admission import HookAdmissionRequest
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import report_verdict
from ethos.domain.land.closeout import closeout_apply_command
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult
from ethos.surface.cli.application import app as root_app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

_app = App(name="hook", help="Hook admission and guard reports.", show=False)
root_app.command(_app)

_LANE_PREWRITE_ACTION = "ethos lane prewrite <path>"
_ADMISSION_OPTIONS = Group("Admission")
_PUSH_OPTIONS = Group("Push")


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
class PushOptions:
    """CLI-only fields for one push admission observation."""

    remote_head: Annotated[str, Parameter(name="--remote-head", group=_PUSH_OPTIONS)] = ""
    remote: Annotated[str, Parameter(name="--remote", group=_PUSH_OPTIONS)] = "origin"
    root: RootOption | None = None
    json_output: JsonFlag = False


_DEFAULT_HOOK_ADMISSION_OPTIONS = _HookAdmissionOptions()
_DEFAULT_PUSH_OPTIONS = PushOptions(remote_head="")


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


@_app.command
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


@_app.command
def pre_push(
    target_ref: str,
    pushed_head: str,
    *,
    options: Annotated[PushOptions, Parameter(name="*")] = _DEFAULT_PUSH_OPTIONS,
) -> None:
    """Evaluate push admission before a ref is pushed to a protected role.

    Pushing to an accepted/candidate ref requires an executed proof bound to the
    pushed HEAD — the same precondition `land` enforces, now bound to the push tail so
    a raw `git push` cannot move a protected ref unproven. Called by the installed pre-push hook.
    """
    repo = resolve_root(options.root)
    report = push_admission_report(
        root=repo,
        target_ref=target_ref,
        pushed_head=pushed_head,
        remote_head=options.remote_head,
        remote_name=options.remote,
    )
    required_gaps = tuple(string_sequence(report.get("required_gaps")))
    next_action = str(report.get("next_action") or "")
    if "accepted_closeout_effect_not_attested" in required_gaps:
        next_action = closeout_apply_command(
            repo,
            accepted_head=options.remote_head,
            candidate_head=pushed_head,
        )
    elif report_verdict(report) != "pass" and not next_action:
        next_action = f"ethos status --root {repo.resolve().as_posix()} --json"
    result = _report_result(
        "hook pre-push",
        report,
        {
            "target_branch": report["target_branch"],
            "role": report["role"],
            "remote": str(report.get("remote_name", options.remote)),
            "decision": _decision_action(report),
        },
        lambda verdict: next_action if verdict != "pass" else "",
    )
    emit(result, json_output=options.json_output, enforce=True)


@_app.command
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


@_app.command(name="run")
def run_hook(
    name: str,
    arguments: Annotated[tuple[str, ...], Parameter(consume_multiple=True)] = (),
) -> None:
    """Execute one installed Git hook through the Python semantic owner."""
    if name not in {"pre-commit", "pre-push", "reference-transaction"}:
        raise SystemExit(1)
    repo = resolve_root(None)
    raise SystemExit(execute_hook(repo, name, arguments, stdin=sys.stdin))


@_app.command
def install(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Install worktree-local Git hook launchers bound to this exact ETHOS runtime."""
    repo = resolve_root(root)
    try:
        runtime = install_hook_launchers(repo)
    except (OSError, ValueError) as error:
        gaps = (f"hook_install_failed:{error}",)
        runtime = {"hooks_path": "", "python": "", "scripts": []}
    else:
        gaps = ()
    result = EthosResult(
        command="hook install",
        verdict="block" if gaps else "pass",
        state="blocked" if gaps else "installed",
        summary={
            "hooks_path": runtime["hooks_path"],
            "python": runtime["python"],
            "wired": not gaps,
            "pack_refs_disabled": not gaps,
        },
        required_gaps=gaps,
        next_action=("git commit — portable admission hooks are active" if not gaps else ""),
        data=runtime,
    )
    emit(result, json_output=json_output, enforce=True)
