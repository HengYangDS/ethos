"""Hook command group — hook-time write admission and hook installation."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures
from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.admission.core import hook_admission_report
from ethos.adapters.repo import git as _gitio
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit as _emit
from ethos.surface.cli._base import hook_app
from ethos.surface.cli._base import resolve_root as _root
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
    repo = _root(root)
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
    _emit(result, json_output, enforce=True)


@hook_app.command
def install(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Install the write-admission git hooks by wiring core.hooksPath to .githooks."""
    repo = _root(root)
    hook_path = repo / ".githooks" / "pre-commit"
    gaps: list[str] = []
    if not hook_path.exists():
        gaps.append("hook_script_missing:.githooks/pre-commit")
    wired = _gitio.set_hooks_path(repo, ".githooks") if not gaps else False
    if not gaps and not wired:
        gaps.append("hooks_path_wire_failed")
    result = EthosResult(
        command="hook install",
        ok=not gaps,
        state="installed" if not gaps else "blocked",
        summary={"hooks_path": ".githooks", "wired": wired},
        required_gaps=tuple(gaps),
        next_actions=(
            ("git commit — the pre-commit admission gate is now active",) if not gaps else ()
        ),
        data={
            "hooks_path": ".githooks",
            "hook_script": ".githooks/pre-commit",
            "wired": wired,
        },
    )
    _emit(result, json_output, enforce=True)
