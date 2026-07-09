"""Root proof command and proof-scope helpers."""

from __future__ import annotations

from typing import cast

import ethos.adapters.repo.git as git
import ethos.domain.status as status_domain
from ethos.adapters.gates.runner import DryRunRunner
from ethos.adapters.gates.runner import LocalSubprocessRunner
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.repository.evidence.core import AdapterProofResult
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from ethos.repository.evidence.core import provenance_envelope
from ethos.repository.evidence.core import trim_output
from ethos.repository.policy.gates import gate_graph
from ethos.repository.policy.gates import gate_registry
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos.surface.cli._gate_runner import run_inprocess_cli_gate
from ethos_core.result import EthosResult

KNOWN_PROOF_SCOPES = frozenset(
    {
        "repository",
        "proof-kernel",
        "code",
        "docs",
        "openspec",
        "quality",
    }
)


def missing_gate_dependency_next_actions(
    *,
    selected_gate_ids: tuple[str, ...],
    validation_gaps: tuple[str, ...],
    current_head: str,
) -> tuple[str, ...]:
    """Return a concrete proof rerun command when selected gates omit dependencies."""
    if not selected_gate_ids:
        return ()

    missing_dependencies = tuple(
        gap.removeprefix("missing_dependency:").split("->", maxsplit=1)[1]
        for gap in validation_gaps
        if gap.startswith("missing_dependency:") and "->" in gap
    )
    if not missing_dependencies:
        return ()

    registry = gate_registry()
    ordered_gate_ids: list[str] = []
    seen: set[str] = set()

    def add_gate_with_dependencies(gate_id: str) -> None:
        if gate_id in seen:
            return
        gate = registry.get(gate_id)
        if gate is None:
            return
        for dependency_id in gate.depends_on:
            add_gate_with_dependencies(dependency_id)
        seen.add(gate_id)
        ordered_gate_ids.append(gate_id)

    for gate_id in selected_gate_ids:
        add_gate_with_dependencies(gate_id)

    if not any(gate_id in ordered_gate_ids for gate_id in missing_dependencies):
        return ()

    command_parts = ["ethos", "prove", "--execute"]
    for gate_id in ordered_gate_ids:
        command_parts.extend(("--gate", gate_id))
    command_parts.extend(("--expect-head", current_head, "--json"))
    return (" ".join(command_parts),)


def proof_scope_binding(scope: str) -> dict[str, object]:
    """Return the proof-scope compatibility binding for command payloads."""
    normalized = " ".join(scope.split()) or "repository"
    known = normalized in KNOWN_PROOF_SCOPES
    return {
        "scope": normalized,
        "accepted": known,
        "known": known,
        "known_scopes": sorted(KNOWN_PROOF_SCOPES),
        "semantics": (
            "proof-boundary metadata; gate selection remains controlled by --gate/--full/profile"
        ),
        "required_gaps": [] if known else [f"unknown_proof_scope:{normalized}"],
    }


def host_probe_boundary(*, host: bool, probe: bool) -> dict[str, object]:
    """Describe optional host-readiness probe flags without minting proof truth."""
    return {
        "requested": host or probe,
        "host": host,
        "probe": probe,
        "evidence_class": "optional_host_readiness",
        "satisfies_repository_proof": False,
        "truth_boundary": "host-local projection",
        "state": "not_requested" if not (host or probe) else "boundary_recorded",
    }


@app.command
def prove(
    *,
    objective: str = "ethos proof",
    scope: str = "repository",
    execute: bool = False,
    gate: tuple[str, ...] = (),
    full: bool = False,
    expect_head: str | None = None,
    host: bool = False,
    probe: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Produce a local proof-readiness summary."""
    repo = resolve_root(root)
    current_head = git.current_head(repo)
    audit = status_domain.audit_for_root(
        repo, openspec_mode="deep" if full else "shape", current_head=current_head
    )
    graph = gate_graph(gate, full=full, root=repo)
    graph_validation = graph.validate()
    gates_by_id = gate_registry()
    runner = (
        LocalSubprocessRunner(inprocess_handler=run_inprocess_cli_gate)
        if execute
        else DryRunRunner()
    )
    proof_runs = tuple(
        ProofRun.from_adapter_result(
            AdapterProofResult(
                action_id=run_result.action_id,
                command=run_result.command,
                exit_code=run_result.exit_code,
                stdout=trim_output(run_result.stdout),
                stderr=trim_output(run_result.stderr),
                adapter_state=run_result.state,
                evidence_class=gates_by_id[run_result.action_id].evidence_class,
                trust_bearing=gates_by_id[run_result.action_id].trust_bearing,
                diagnostics=run_result.diagnostics,
            )
        )
        for run_result in (runner.run(node, root=repo) for node in graph.ordered_nodes())
    )
    evidence = EvidenceSet.from_runs(
        id=f"ethos:{objective}",
        head=current_head,
        runs=proof_runs,
        durability="local",
    )
    verdicts_ok = all(run.verdict == "passed" for run in proof_runs)
    trust_bearing_runs = tuple(run for run in proof_runs if run.trust_bearing)
    trust_bearing_ok = bool(trust_bearing_runs) and all(
        run.state == "proven" for run in trust_bearing_runs
    )
    runs_ok = (
        verdicts_ok and trust_bearing_ok
        if execute
        else all(run.state == "planned" for run in proof_runs)
    )
    failed_gate_gaps: tuple[str, ...] = (
        tuple(f"gate_failed:{run.action_id}" for run in proof_runs if run.verdict != "passed")
        if execute
        else ()
    )
    proof_gaps: tuple[str, ...] = ("full_proof_requires_execute",) if full and not execute else ()
    trust_gaps: tuple[str, ...] = (
        ("trust_bearing_proof_missing",) if execute and verdicts_ok and not trust_bearing_ok else ()
    )
    head_gaps: tuple[str, ...] = (
        ("expected_head_mismatch",)
        if expect_head is not None and expect_head != current_head
        else ()
    )
    scope_binding = proof_scope_binding(scope)
    scope_gaps = tuple(cast("list[str]", scope_binding["required_gaps"]))
    host_probe = host_probe_boundary(host=host, probe=probe)
    ok = (
        bool(audit["ok"])
        and runs_ok
        and graph_validation.ok
        and not failed_gate_gaps
        and not proof_gaps
        and not trust_gaps
        and not head_gaps
        and not scope_gaps
    )
    result_state = "proven" if ok and execute else "ready" if ok else "gapped"
    if result_state == "proven":
        record_executed_proof(repo, evidence.to_dict())
    dependency_next_actions = missing_gate_dependency_next_actions(
        selected_gate_ids=gate,
        validation_gaps=graph_validation.gaps,
        current_head=current_head,
    )
    next_actions = dependency_next_actions or (
        ("ethos land",)
        if result_state == "proven"
        else ("ethos prove --execute",)
        if result_state == "ready"
        else ("ethos audit --mode deep",)
    )
    result = EthosResult(
        command="prove",
        ok=ok,
        state=result_state,
        summary={
            "objective": objective,
            "evidence_digest": evidence.digest,
            "gate_count": len(proof_runs),
        },
        required_gaps=(
            tuple(audit["required_gaps"])
            + tuple(graph_validation.gaps)
            + failed_gate_gaps
            + proof_gaps
            + trust_gaps
            + head_gaps
            + scope_gaps
        ),
        next_actions=next_actions,
        governance_context=cast("dict[str, object]", audit["governance_context"]),
        data={
            "governance_context": audit["governance_context"],
            "repository_audit": audit,
            "executed": execute,
            "scope": scope_binding["scope"],
            "scope_binding": scope_binding,
            "host_probe": host_probe,
            "action_graph": graph.to_dict(),
            "evidence": evidence.to_dict(),
            "provenance": provenance_envelope(evidence),
            "expected_head": {
                "expected": expect_head or "",
                "current": current_head,
                "ok": expect_head is None or expect_head == current_head,
            },
        },
    )
    emit(result, json_output=json_output, enforce=False)
