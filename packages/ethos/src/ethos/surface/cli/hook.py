"""Hook command group — hook-time write admission and hook installation."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures
from typing import Annotated

from cyclopts import Parameter

import ethos.adapters.repo.git as git_adapter
from ethos.adapters.admission.core import hook_admission_report
from ethos.adapters.admission.core import push_admission_report
from ethos.adapters.admission.core import ref_move_admission_report
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import hook_app
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.result import EthosResult


@hook_app.command
def admit(
    layer: str,
    paths: tuple[Path, ...] = (),
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
        root=repo,
        layer=layer,
        paths=[path if path.is_absolute() else repo / path for path in paths],
        editor_root=editor_root,
        expected_root=expected_root,
        require_editor_root=require_editor_root,
        command=command,
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
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos lane prewrite <path>",) if not report["ok"] else (),
        data=report,
    )
    emit(result, json_output=json_output, enforce=True)


@hook_app.command
def pre_push(
    target_ref: str,
    pushed_head: str,
    *,
    remote_head: Annotated[str, Parameter(name="--remote-head")] = "",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Evaluate push admission before a ref is pushed to a protected role.

    Pushing to an accepted/candidate ref requires an executed proof bound to the
    pushed HEAD — the same precondition `land` enforces, now bound to the push tail so
    a raw `git push` cannot move a protected ref unproven. Called by .githooks/pre-push.
    """
    repo = resolve_root(root)
    report = push_admission_report(
        root=repo, target_ref=target_ref, pushed_head=pushed_head, remote_head=remote_head
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
            "decision": decision_action,
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=(("ethos prove --execute --expect-head <head>",) if not report["ok"] else ()),
        data=report,
    )
    emit(result, json_output=json_output, enforce=True)


@hook_app.command
def ref_transaction(
    ref_name: str,
    old_value: str,
    new_value: str,
    *,
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
    report = ref_move_admission_report(
        root=repo, ref_name=ref_name, old_value=old_value, new_value=new_value
    )
    decision = report.get("decision", {})
    decision_action = decision.get("action", "") if isinstance(decision, dict) else ""
    result = EthosResult(
        command="hook ref-transaction",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={"branch": report["branch"], "decision": decision_action},
        required_gaps=tuple(report["required_gaps"]),
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
    if not gaps and not wired:
        gaps.append("hooks_path_wire_failed")
    if wired:
        # Record the accepted branch so the reference-transaction hook knows which ref
        # to fail-closed on (the hook runs as a plain shell script with no ETHOS import).
        accepted = load_branch_role_policy(repo).accepted_branch
        git_adapter.set_config(repo, "ethos.acceptedBranch", accepted)
    result = EthosResult(
        command="hook install",
        ok=not gaps,
        state="installed" if not gaps else "blocked",
        summary={"hooks_path": ".githooks", "wired": wired},
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
        },
    )
    emit(result, json_output=json_output, enforce=True)
