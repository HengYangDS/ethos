"""Dependency-ready execution with bounded readers and exclusive writers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from concurrent.futures import FIRST_COMPLETED
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from contextlib import ExitStack
from contextvars import copy_context
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import replace
from graphlib import TopologicalSorter
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.gates.javascript.execution import prepare_command
from ethos.adapters.gates.javascript.execution import retain_attempt
from ethos.adapters.gates.native.attempt import gate_attempt
from ethos.adapters.gates.native.attempt import gate_execution
from ethos.adapters.gates.verification import assert_provider_execution_source
from ethos.adapters.gates.verification import classify_action_result
from ethos.adapters.gates.verification import provider_reports
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import command_scope
from ethos.adapters.repo.dependency_acceptance import captured_dependency_acceptance
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.worktree_postimage import observe_execution_source
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.proof.plan import execution_source_gaps
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import execution_succeeded
from ethos.contracts.verdict import reduce_verdicts
from ethos.repository.policy.gates import gate_execution_identity
from ethos.repository.policy.quality.dependency_acceptance import native_dependency_audit_scope

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping

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
    verification: dict[str, object] | None = None
    started_after_seconds: float | None = None
    duration_seconds: float | None = None


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
        result = None
        try:
            with ExitStack() as attempt_scope:
                result = self._run(node, gate, root=root, attempt_scope=attempt_scope)
        except ProcessExecutionError as error:
            if error.reason != "native_attempt_source_binding":
                raise
            failed = result or ActionRunResult(node.id, node.command, "block", None)
            return replace(
                failed,
                verdict="block",
                diagnostics=(
                    *failed.diagnostics,
                    {
                        "kind": "native_source_binding",
                        **error.evidence(),
                        "required_gaps": [error.code],
                    },
                ),
            )
        else:
            return result

    def _run(
        self, node: PlanNode, gate: Gate, *, root: Path, attempt_scope: ExitStack
    ) -> ActionRunResult:
        deadline = monotonic() + gate.timeout_seconds if gate.timeout_seconds else None
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
        invoked = Path(command[0])
        executable = (
            str(invoked if invoked.is_absolute() else root / invoked)
            if invoked.is_absolute()
            or any(separator and separator in command[0] for separator in (os.sep, os.altsep))
            else shutil.which(command[0])
        )
        execution_command = (
            (str(Path(executable).absolute()), *command[1:]) if executable else command
        )
        native_evidence = None
        node_attempt = None
        if "ethos.adapters.gates.code_quality:behavior_report" in gate.verification_providers and (
            preparation := prepare_command(root, execution_command)
        ):
            node_attempt = attempt_scope.enter_context(preparation)
        try:
            completed, native_evidence = gate_attempt(
                root,
                gate,
                execution_command,
                timeout=max(0, deadline - monotonic()) if deadline else None,
                env=node_attempt.environment() if node_attempt is not None else None,
                remove_env=("NODE_OPTIONS", "NODE_PATH", "NODE_V8_COVERAGE")
                if node_attempt is not None
                else (),
            )
        except subprocess.TimeoutExpired as exc:
            stdout = (
                exc.stdout.decode(errors="replace")
                if isinstance(exc.stdout, bytes)
                else exc.stdout or ""
            )
            stderr = (
                exc.stderr.decode(errors="replace")
                if isinstance(exc.stderr, bytes)
                else exc.stderr or ""
            )
            observation: dict[str, object] = {}
            if node_attempt is not None:
                observed = {
                    "language": "javascript",
                    "source_tree": node_attempt.source_tree,
                    "raw_directory": str(node_attempt.output / "raw"),
                    "argv": execution_command,
                    "timeout": exc.timeout,
                    "stdout": stdout,
                    "stderr": stderr,
                    "verdict": "unknown",
                    "required_gaps": [f"gate_timeout:{node.id}"],
                }
                observation = {
                    "observation": {"artifact": retain_attempt(root, node_attempt.output, observed)}
                }
            return ActionRunResult(
                action_id=node.id,
                command=node.command,
                verdict="unknown",
                exit_code=124,
                stdout=stdout,
                stderr=stderr,
                diagnostics=(
                    {
                        "kind": "gate_timeout",
                        "timeout_seconds": exc.timeout,
                        "required_gaps": [f"gate_timeout:{node.id}"],
                        **observation,
                    },
                ),
            )
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
        timeout_gap = (
            f"gate_timeout:{node.id}"
            if native_evidence is not None and "native_execution_timeout" in native_evidence.gaps
            else None
        )
        if (
            scope := native_dependency_audit_scope(gate.model_dump(mode="python"))
        ) and timeout_gap is None:
            decision = captured_dependency_acceptance(
                completed.stdout,
                head=current_tracked_head(root),
                source=lambda name: (root / name).read_bytes(),
                scope=scope,
            )
            verdict = "block" if completed.returncode != 0 else decision["verdict"]
            diagnostics = (
                {
                    "kind": "dependency_acceptance",
                    "verdict": verdict,
                    "required_gaps": [] if verdict == "pass" else [decision["reason"]],
                },
            )
        else:
            verdict, diagnostics = classify_action_result(
                exit_code=completed.returncode,
                stdout=completed.stdout,
                timeout_gap=timeout_gap,
            )
        execution = ActionRunResult(
            action_id=node.id,
            command=node.command,
            verdict=verdict,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            diagnostics=diagnostics,
        )
        native = gate_execution(
            root,
            node.command,
            command,
            completed,
            executable=execution_command[0] if executable else "",
            evidence=native_evidence,
        )
        verification: dict[str, object] | None = (
            {
                "gate": gate.id,
                "native_artifact": native.evidence.artifact,
                "providers": [],
            }
            if native.evidence is not None
            else None
        )
        if (verdict == "pass" or node_attempt is not None) and gate.verification_providers:
            reports, verdict, provider_diagnostics = provider_reports(
                gate.id,
                gate.verification_providers,
                root,
                timeout_seconds=max(0, deadline - monotonic()) if deadline else None,
                execution=replace(native, node_attempt=node_attempt),
            )
            verdict = reduce_verdicts(execution.verdict, verdict)
            verification = {
                **(verification or {}),
                "gate": gate.id,
                "providers": reports,
            }
            diagnostics = (*diagnostics, *provider_diagnostics)
        return replace(
            execution,
            verdict=verdict,
            exit_code=completed.returncode
            if native.evidence is not None
            else (completed.returncode if verification is None else int(verdict != "pass")),
            diagnostics=diagnostics,
            verification=verification,
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
    checks: list[dict[str, Any]] = []
    gaps = ["proof_head_missing"] if not head else []
    if expect_head is not None and expect_head != head:
        gaps.append("expected_head_mismatch")
    policy = None

    def resolve():
        return resolve_gate_policy(
            root,
            tree_ref=head,
            gate_ids=gate_ids,
            full=full,
            selected_obligations=bool(gate_ids) and not full,
        )

    try:
        policy = resolve() if not gaps else None
        if policy is not None:
            gaps.extend(policy.gaps)
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
            checks = [asdict(result) for result in results]
            gaps.extend(policy.result_gaps(checks, source_tree=tree))
            if exact and (
                current_tracked_head(root) != head
                or observe_execution_source(root, head, tree) != source
                or resolve().digest != policy.digest
            ):
                gaps.append("proof_execution_source_changed")
    except ValueError as error:
        gaps.append(str(error))
    return {
        "verdict": "block" if gaps or not checks else "pass",
        "head": head,
        "policy_digest": policy.digest if policy is not None else "",
        "execution_source": source,
        "executed": bool(checks),
        "checks": checks,
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
    occupied = list(active)
    reserved = sum(min(gates[name].cpu_reservation, capacity) for name in active)
    for node in candidates:
        if len(occupied) >= capacity:
            break
        demand = min(gates[node.id].cpu_reservation, capacity)
        if reserved + demand <= capacity and not any(
            gates[node.id].conflicts_with(gates[other]) for other in occupied
        ):
            selected.append(node)
            occupied.append(node.id)
            reserved += demand
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
            selected = _ready_checks(scheduled, gates, ready, tuple(running.values()), limit)
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
    reports, verdict, diagnostics = provider_reports(
        gate.id, gate.providers, root, timeout_seconds=gate.timeout_seconds
    )
    payload = {"verdict": verdict, "gate": gate.id, "providers": reports}
    return ActionRunResult(
        action_id=node.id,
        command=node.command,
        verdict=verdict,
        exit_code=0 if verdict == "pass" else 1,
        stdout=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        diagnostics=diagnostics,
    )
