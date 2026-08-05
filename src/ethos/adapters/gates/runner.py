from __future__ import annotations

import importlib
import inspect
import json
import subprocess
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.repo.git import current_head
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import report_verdict
from ethos.repository.policy.gates import gate_execution_identity

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.gates import Gate
    from ethos.contracts.plan import PlanNode


@dataclass(frozen=True, slots=True)
class ActionRunResult:
    action_id: str
    command: tuple[str, ...]
    verdict: Verdict
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    diagnostics: tuple[dict[str, Any], ...] = ()


def classify_action_result(
    *,
    exit_code: int | None,
    stdout: str,
) -> tuple[Verdict, tuple[dict[str, Any], ...]]:
    if exit_code != 0:
        return "block", ()
    return _ethos_result_verdict(stdout)


def _ethos_result_verdict(stdout: str) -> tuple[Verdict, tuple[dict[str, Any], ...]]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return "pass", ()
    if not isinstance(payload, dict) or "command" not in payload:
        return "pass", ()
    raw_verdict = payload.get("verdict")
    if raw_verdict not in {"pass", "block", "unknown"}:
        return "unknown", (
            {
                "kind": "ethos_result",
                "verdict": "unknown",
                "state": str(payload.get("state", "")),
                "required_gaps": ["ethos_result_verdict_missing_or_invalid"],
            },
        )
    required_gaps = _strings(payload.get("required_gaps"))
    warnings = _strings(payload.get("warnings"))
    diagnostic_gaps = _diagnostic_gaps(payload.get("diagnostics"), "ethos_result")
    gaps = tuple(dict.fromkeys((*required_gaps, *diagnostic_gaps)))
    verdict = report_verdict(payload)
    if verdict == "pass":
        return verdict, ()
    warning_gaps = tuple(f"ethos_result_warning:{warning}" for warning in warnings)
    return verdict, (
        {
            "kind": "ethos_result",
            "verdict": verdict,
            "state": str(payload.get("state", "")),
            "required_gaps": list(dict.fromkeys((*gaps, *warning_gaps))),
        },
    )


class DryRunRunner:
    def run(self, node: PlanNode, _gate: Gate, *, root: Path) -> ActionRunResult:
        root.resolve(strict=True)
        return ActionRunResult(
            action_id=node.id,
            command=node.command,
            verdict="unknown",
            exit_code=None,
        )


class LocalGateRunner:
    """Execute a declared provider directly or an external adapter command."""

    def run(self, node: PlanNode, gate: Gate, *, root: Path) -> ActionRunResult:
        if node.command != gate_execution_identity(gate):
            return ActionRunResult(
                action_id=node.id,
                command=node.command,
                verdict="block",
                exit_code=1,
                diagnostics=(
                    {
                        "kind": "gate_execution_identity",
                        "required_gaps": [f"gate_execution_identity_mismatch:{node.id}"],
                    },
                ),
            )
        if gate.providers:
            return _run_providers(node, gate, root)
        command = gate.command
        try:
            completed = subprocess.run(
                list(command),
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
        except FileNotFoundError as exc:
            missing = str(exc.filename or command[0])
            return ActionRunResult(
                action_id=node.id,
                command=node.command,
                verdict="block",
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
        verdict, diagnostics = classify_action_result(
            exit_code=completed.returncode,
            stdout=completed.stdout,
        )
        return ActionRunResult(
            action_id=node.id,
            command=node.command,
            verdict=verdict,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            diagnostics=diagnostics,
        )


def proof_waves(
    nodes: tuple[PlanNode, ...], gates: Mapping[str, Gate], *, capacity: int
) -> tuple[tuple[PlanNode, ...], ...]:
    """Partition one admitted DAG into deterministic safe execution waves."""
    if capacity < 1:
        message = "proof_node_capacity_invalid"
        raise ValueError(message)
    remaining = list(nodes)
    completed: set[str] = set()
    waves: list[tuple[PlanNode, ...]] = []
    while remaining:
        ready = [node for node in remaining if set(node.depends_on) <= completed]
        if not ready:
            message = "proof_plan_dependencies_unresolved"
            raise ValueError(message)
        write_ready = next((node for node in ready if gates[node.id].writes_files), None)
        read_only = [node for node in ready if not gates[node.id].writes_files]
        wave = (write_ready,) if write_ready is not None else tuple(read_only[:capacity])
        waves.append(wave)
        completed.update(node.id for node in wave)
        selected = {node.id for node in wave}
        remaining = [node for node in remaining if node.id not in selected]
    return tuple(waves)


def run_gate_waves(
    runner: DryRunRunner | LocalGateRunner,
    nodes: tuple[PlanNode, ...],
    gates: Mapping[str, Gate],
    *,
    root: Path,
    capacity: int,
    parallel: bool,
) -> tuple[ActionRunResult, ...]:
    """Execute safe proof waves while preserving canonical result order."""
    results: list[ActionRunResult] = []
    for wave in proof_waves(nodes, gates, capacity=capacity):
        if parallel and len(wave) > 1:
            with ThreadPoolExecutor(max_workers=len(wave)) as executor:
                results.extend(
                    executor.map(lambda node: runner.run(node, gates[node.id], root=root), wave)
                )
        else:
            results.extend(runner.run(node, gates[node.id], root=root) for node in wave)
    return tuple(results)


def _run_providers(node: PlanNode, gate: Gate, root: Path) -> ActionRunResult:
    reports: list[dict[str, object]] = []
    diagnostics: list[dict[str, Any]] = []
    verdicts: list[Verdict] = []
    for reference in gate.providers:
        try:
            report = _provider_report(reference, root)
        except (
            AttributeError,
            ImportError,
            OSError,
            RuntimeError,
            subprocess.SubprocessError,
            TypeError,
            ValueError,
        ) as exc:
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
        gaps = _strings(report.get("required_gaps"))
        warnings = _strings(report.get("warnings"))
        warning_gaps = tuple(
            f"gate_provider_warning:{gate.id}:{reference}:{warning}" for warning in warnings
        )
        diagnostic_gaps = _diagnostic_gaps(
            report.get("diagnostics"), f"gate_provider_diagnostic:{gate.id}:{reference}"
        )
        provider_gaps = tuple(dict.fromkeys((*gaps, *warning_gaps, *diagnostic_gaps)))
        verdict = report_verdict(
            {
                **report,
                "required_gaps": provider_gaps,
            }
        )
        if verdict == "block" and not provider_gaps:
            provider_gaps = (f"gate_provider_blocked:{gate.id}:{reference}",)
        elif verdict == "unknown" and not provider_gaps:
            provider_gaps = (f"gate_provider_unknown:{gate.id}:{reference}",)
        verdicts.append(verdict)
        if verdict != "pass":
            diagnostics.append(
                {
                    "kind": "gate_provider",
                    "provider": reference,
                    "verdict": verdict,
                    "required_gaps": list(provider_gaps),
                }
            )
    if len(reports) != len(gate.providers) or "block" in verdicts:
        verdict: Verdict = "block"
    elif "unknown" in verdicts:
        verdict = "unknown"
    else:
        verdict = "pass"
    payload = {"verdict": verdict, "gate": gate.id, "providers": reports}
    return ActionRunResult(
        action_id=node.id,
        command=node.command,
        verdict=verdict,
        exit_code=0 if verdict == "pass" else 1,
        stdout=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        diagnostics=tuple(diagnostics),
    )


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _diagnostic_gaps(value: object, prefix: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    gaps = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        severity = str(item.get("severity", "")).lower()
        if severity not in {"warning", "error"}:
            continue
        message = str(item.get("message") or item.get("code") or severity)
        gaps.append(f"{prefix}:{severity}:{message}")
    return tuple(gaps)


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
