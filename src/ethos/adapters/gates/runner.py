from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ethos.contracts.plan import PlanNode


@dataclass(frozen=True, slots=True)
class ActionRunResult:
    action_id: str
    command: tuple[str, ...]
    state: str
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    diagnostics: tuple[dict[str, Any], ...] = ()


def classify_action_result(
    *,
    exit_code: int | None,
    stdout: str,
) -> tuple[str, tuple[dict[str, Any], ...]]:
    if exit_code != 0:
        return "failed", ()
    diagnostics = _ethos_result_diagnostics(stdout)
    if diagnostics:
        return "failed", diagnostics
    return "passed", ()


def _ethos_result_diagnostics(stdout: str) -> tuple[dict[str, Any], ...]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, dict) or payload.get("ok") is not False:
        return ()
    return (
        {
            "kind": "ethos_result",
            "ok": False,
            "state": str(payload.get("state", "")),
            "required_gaps": [str(gap) for gap in payload.get("required_gaps", []) if str(gap)],
        },
    )


class DryRunRunner:
    def run(self, node: PlanNode, *, root: Path) -> ActionRunResult:
        root.resolve(strict=True)
        return ActionRunResult(
            action_id=node.id,
            command=node.command,
            state="planned",
            exit_code=None,
        )


InProcessHandler = Callable[[PlanNode, Path], ActionRunResult | None]


class LocalSubprocessRunner:
    def __init__(self, *, inprocess_handler: InProcessHandler | None = None) -> None:
        self._inprocess_handler = inprocess_handler

    def run(self, node: PlanNode, *, root: Path) -> ActionRunResult:
        if self._inprocess_handler is not None:
            inprocess = self._inprocess_handler(node, root)
            if inprocess is not None:
                return inprocess
        try:
            completed = subprocess.run(
                list(node.command),
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError as exc:
            missing = str(exc.filename or node.command[0])
            return ActionRunResult(
                action_id=node.id,
                command=node.command,
                state="failed",
                exit_code=127,
                stderr=str(exc),
                diagnostics=(
                    {
                        "kind": "command_not_found",
                        "missing": missing,
                        "cwd": str(root),
                        "required_gaps": [f"missing_command:{missing}"],
                    },
                ),
            )
        state, diagnostics = classify_action_result(
            exit_code=completed.returncode,
            stdout=completed.stdout,
        )
        return ActionRunResult(
            action_id=node.id,
            command=node.command,
            state=state,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            diagnostics=diagnostics,
        )
