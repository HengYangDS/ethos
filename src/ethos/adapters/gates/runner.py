"""Dependency-ready execution with bounded readers and exclusive writers."""

from __future__ import annotations

import importlib
import inspect
import json
import os
import subprocess
from collections.abc import Mapping
from concurrent.futures import FIRST_COMPLETED
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from contextvars import copy_context
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import replace
from graphlib import TopologicalSorter
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import ethos
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import command_scope
from ethos.adapters.process import run_command
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.adapters.repo.worktree_postimage import observe_execution_source
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.proof.plan import execution_source_gaps
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import execution_succeeded
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.gates import PRODUCT_PROVIDER_SOURCE
from ethos.repository.policy.gates import gate_execution_identity
from ethos.repository.policy.gates import source_paths_for_gate

if TYPE_CHECKING:
    from collections.abc import Callable

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
    started_after_seconds: float | None = None
    duration_seconds: float | None = None


def classify_action_result(
    *,
    exit_code: int | None,
    stdout: str,
) -> tuple[Verdict, tuple[dict[str, Any], ...]]:
    if exit_code != 0:
        return "block", ()
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return "pass", ()
    if not isinstance(payload, dict) or "command" not in payload:
        return "pass", ()
    raw_verdict = payload.get("verdict")
    if not isinstance(raw_verdict, str) or raw_verdict not in {"pass", "block", "unknown"}:
        return "unknown", (
            {
                "kind": "ethos_result",
                "verdict": "unknown",
                "state": str(payload.get("state", "")),
                "required_gaps": ["ethos_result_verdict_missing_or_invalid"],
            },
        )
    required_gaps = string_sequence(payload.get("required_gaps"), drop_empty=True)
    warnings = string_sequence(payload.get("warnings"), drop_empty=True)
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
            completed = run_command(root, command)
        except ProcessExecutionError as exc:
            if not isinstance(exc.__cause__, FileNotFoundError):
                raise
            missing = str(exc.__cause__.filename or command[0])
            return ActionRunResult(
                action_id=node.id,
                command=node.command,
                verdict="block",
                exit_code=127,
                stderr=str(exc.__cause__),
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


def observe_gate_execution(
    root: Path,
    *,
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
    expect_head: str | None = None,
) -> dict[str, Any]:
    """Execute one source-bound quality observation without granting mutation authority."""
    head = current_tracked_head(root)
    exact = full or expect_head is not None
    tree = current_tree(root, head) if head and exact else ""
    source: dict[str, str] = {}
    results: tuple[ActionRunResult, ...] = ()
    gaps = ["proof_head_missing"] if not head else []
    if expect_head is not None and expect_head != head:
        gaps.append("expected_head_mismatch")
    policy = None
    try:
        if not gaps:
            policy = resolve_gate_policy(root, tree_ref=head, gate_ids=gate_ids, full=full)
        if policy is not None:
            gaps.extend(policy.gaps)
            if not policy.nodes:
                gaps.append("proof_floor_empty")
        if not gaps and exact:
            source = observe_execution_source(root, head, tree)
            gaps.extend(
                execution_source_gaps({"tree": tree, "values": {"execution_source": source}})
            )
        if not gaps and policy is not None:
            results = run_gate_graph(
                LocalGateRunner(),
                policy.nodes,
                policy.registry,
                root=root,
                capacity=max(1, os.cpu_count() or 1),
                parallel=True,
            )
            gaps.extend(
                policy.result_gaps(tuple(asdict(result) for result in results), source_tree=tree)
            )
            if exact and (
                current_tracked_head(root) != head
                or observe_execution_source(root, head, tree) != source
                or resolve_gate_policy(root, tree_ref=head, gate_ids=gate_ids, full=full).digest
                != policy.digest
            ):
                gaps.append("proof_execution_source_changed")
    except ValueError as error:
        gaps.append(str(error))
    return {
        "verdict": "block" if gaps or not results else "pass",
        "head": head,
        "policy_digest": policy.digest if policy is not None else "",
        "execution_source": source,
        "executed": bool(results),
        "checks": [asdict(result) for result in results],
        "required_gaps": gaps,
    }


def _scheduled_nodes(
    nodes: tuple[PlanNode, ...],
    gates: Mapping[str, Gate],
) -> tuple[PlanNode, ...]:
    """Derive selected preflight ordering without changing proof-policy inputs."""
    ordered = TransitionPlan.closure(nodes)
    postexecution: set[str] = set()
    execution_roots: set[str] = set()
    for node in ordered:
        if postexecution.intersection(node.depends_on):
            postexecution.add(node.id)
        elif gates[node.id].kind in {"test", "package"}:
            postexecution.add(node.id)
            execution_roots.add(node.id)
    readiness = tuple(node.id for node in ordered if node.id not in postexecution)
    return tuple(
        node.model_copy(update={"depends_on": tuple(dict.fromkeys((*node.depends_on, *readiness)))})
        if node.id in execution_roots
        else node
        for node in nodes
    )


def _ready_checks(
    nodes: tuple[PlanNode, ...],
    gates: Mapping[str, Gate],
    ready: set[str],
    active: tuple[str, ...],
    capacity: int,
) -> tuple[PlanNode, ...]:
    """Choose a bounded compatible ready set without introducing a global wave."""
    selected: list[PlanNode] = []
    candidates = sorted(
        (node for node in nodes if node.id in ready),
        key=lambda node: not gates[node.id].writes_files,
    )
    for node in candidates:
        if len(selected) >= capacity:
            break
        occupied = (*active, *(item.id for item in selected))
        if not any(gates[node.id].conflicts_with(gates[other]) for other in occupied):
            selected.append(node)
    return tuple(selected)


def run_gate_graph(
    runner: DryRunRunner | LocalGateRunner,
    nodes: tuple[PlanNode, ...],
    gates: Mapping[str, Gate],
    *,
    root: Path,
    capacity: int,
    parallel: bool,
    on_schedule: Callable[[str], None] | None = None,
    on_result: Callable[[ActionRunResult], None] | None = None,
) -> tuple[ActionRunResult, ...]:
    """Run ready nonconflicting checks once and return canonical plan order."""
    if capacity < 1:
        message = "proof_node_capacity_invalid"
        raise ValueError(message)
    scheduled = _scheduled_nodes(nodes, gates)
    if not isinstance(runner, DryRunRunner):
        assert_provider_execution_source(root, tuple(gates[node.id] for node in nodes))
    graph = TopologicalSorter({node.id: node.depends_on for node in scheduled})
    graph.prepare()
    ready: set[str] = set()
    results: dict[str, ActionRunResult] = {}
    running = {}
    limit = capacity if parallel else 1
    epoch = monotonic()
    scheduled_event = on_schedule or (lambda _action_id: None)
    completed_event = on_result or (lambda _result: None)

    with ThreadPoolExecutor(max_workers=limit) as executor, command_scope():
        while graph.is_active():
            ready.update(graph.get_ready())
            selected = _ready_checks(
                scheduled, gates, ready, tuple(running.values()), limit - len(running)
            )
            for node in selected:
                ready.remove(node.id)
                scheduled_event(node.id)
                if not parallel or isinstance(runner, DryRunRunner):
                    results[node.id] = _run_ready_gate(
                        runner, node, gates[node.id], results, root, epoch
                    )
                    completed_event(results[node.id])
                    graph.done(node.id)
                else:
                    running[
                        executor.submit(
                            copy_context().run,
                            _run_ready_gate,
                            runner,
                            node,
                            gates[node.id],
                            results,
                            root,
                            epoch,
                        )
                    ] = node.id
            if selected:
                continue
            if running:
                completed, _pending = wait(running, return_when=FIRST_COMPLETED)
                for future in completed:
                    node_id = running.pop(future)
                    results[node_id] = future.result()
                    completed_event(results[node_id])
                    graph.done(node_id)
    return tuple(results[node.id] for node in nodes)


def _run_ready_gate(
    runner: DryRunRunner | LocalGateRunner,
    node: PlanNode,
    gate: Gate,
    results: Mapping[str, ActionRunResult],
    root: Path,
    epoch: float,
) -> ActionRunResult:
    """Execute only when every settled prerequisite carries successful evidence."""
    gaps = [
        f"gate_dependency_not_proven:{key}"
        for key in node.depends_on
        if not execution_succeeded(asdict(results[key]))
    ]
    if gaps and not isinstance(runner, DryRunRunner):
        return ActionRunResult(
            node.id,
            node.command,
            "block",
            None,
            diagnostics=({"kind": "gate_dependency", "required_gaps": gaps},),
        )
    started = monotonic()
    result = runner.run(node, gate, root=root)
    return (
        result
        if isinstance(runner, DryRunRunner)
        else replace(
            result, started_after_seconds=started - epoch, duration_seconds=monotonic() - started
        )
    )


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
        gaps = string_sequence(report.get("required_gaps"), drop_empty=True)
        warnings = string_sequence(report.get("warnings"), drop_empty=True)
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
    verdict = reduce_verdicts(*verdicts) if len(reports) == len(gate.providers) else "block"
    payload = {"verdict": verdict, "gate": gate.id, "providers": reports}
    return ActionRunResult(
        action_id=node.id,
        command=node.command,
        verdict=verdict,
        exit_code=0 if verdict == "pass" else 1,
        stdout=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        diagnostics=tuple(diagnostics),
    )


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


def assert_provider_execution_source(root: Path, gates: tuple[Gate, ...]) -> None:
    """Reject candidate-bound checks running from a different implementation before effects."""
    bound = tuple(
        (gate.id, reference)
        for gate in gates
        if gate.providers
        for reference, relative in zip(gate.providers, source_paths_for_gate(gate), strict=True)
        if not relative.startswith(PRODUCT_PROVIDER_SOURCE) and (root / relative).is_file()
    )
    package = Path(ethos.__file__).resolve()
    if not bound or package == (root / "src/ethos/__init__.py").resolve():
        return
    try:
        identity = invoking_build_identity()
        head = current_tracked_head(root)
        if head == identity.source_commit and current_tree(root, head) == identity.source_tree:
            return
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        pass
    gate_id, reference = bound[0]
    message = f"gate_provider_source_mismatch:{gate_id}:{reference}"
    raise ProcessExecutionError(
        message,
        reason="candidate_provider_execution_requires_matching_source",
        cwd=str(root),
        observation={
            "runner_module_path": str(package),
            "required_gaps": [f"gate_provider_source_mismatch:{name}:{ref}" for name, ref in bound],
            "next_action": "run proof from the admitted checkout's locked Python environment",
        },
    )
