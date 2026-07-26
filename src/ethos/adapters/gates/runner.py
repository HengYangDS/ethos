from __future__ import annotations

import importlib
import inspect
import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.repo.git import current_head

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.gates import GateDescriptor
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
    def run(self, node: PlanNode, gate: GateDescriptor, *, root: Path) -> ActionRunResult:
        root.resolve(strict=True)
        return ActionRunResult(
            action_id=node.id,
            command=gate.command,
            state="planned",
            exit_code=None,
        )


class LocalGateRunner:
    """Execute a declared provider directly or an external adapter command."""

    def run(self, node: PlanNode, gate: GateDescriptor, *, root: Path) -> ActionRunResult:
        if gate.providers:
            return _run_providers(node, gate, root)
        try:
            completed = subprocess.run(
                list(gate.command),
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError as exc:
            missing = str(exc.filename or gate.command[0])
            return ActionRunResult(
                action_id=node.id,
                command=gate.command,
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
            command=gate.command,
            state=state,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            diagnostics=diagnostics,
        )


def _run_providers(node: PlanNode, gate: GateDescriptor, root: Path) -> ActionRunResult:
    reports: list[dict[str, object]] = []
    diagnostics: list[dict[str, Any]] = []
    for reference in gate.providers:
        try:
            report = _provider_report(reference, root)
        except Exception as exc:
            diagnostics.append(
                {
                    "kind": "gate_provider_error",
                    "provider": reference,
                    "error": f"{type(exc).__name__}: {exc}",
                    "required_gaps": [f"gate_provider_error:{gate.id}:{reference}"],
                }
            )
            continue
        reports.append({"provider": reference, "report": dict(report)})
        raw_gaps = report.get("required_gaps", ())
        gaps = (
            [str(gap) for gap in raw_gaps if str(gap)]
            if isinstance(raw_gaps, (list, tuple))
            else []
        )
        if report.get("ok") is not True or gaps:
            diagnostics.append(
                {
                    "kind": "gate_provider",
                    "provider": reference,
                    "ok": report.get("ok") is True,
                    "required_gaps": gaps or [f"gate_provider_blocked:{gate.id}:{reference}"],
                }
            )
    ok = not diagnostics and len(reports) == len(gate.providers)
    payload = {"ok": ok, "gate": gate.id, "providers": reports}
    return ActionRunResult(
        action_id=node.id,
        command=("provider", *gate.providers),
        state="passed" if ok else "failed",
        exit_code=0 if ok else 1,
        stdout=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        diagnostics=tuple(diagnostics),
    )


def _provider_report(reference: str, root: Path) -> Mapping[str, object]:
    module_name, _, attribute = reference.partition(":")
    provider = getattr(importlib.import_module(module_name), attribute)
    parameters = inspect.signature(provider).parameters
    kwargs = {"current_head": current_head(root)} if "current_head" in parameters else {}
    value = provider(root, **kwargs)
    if not isinstance(value, Mapping):
        message = f"gate provider must return a mapping: {reference}"
        raise TypeError(message)
    return cast("Mapping[str, object]", value)
