"""Root proof command and proof-scope helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Annotated
from typing import cast

from cyclopts import Parameter

import ethos.adapters.repo.git as git
import ethos.domain.status as status_domain
from ethos.adapters.gates.runner import DryRunRunner
from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.adapters.openspec.core import openspec_governance_report
from ethos.adapters.repo.dirty.core import change_scope_paths_from_status
from ethos.adapters.repo.status.core import workspace_status
from ethos.domain.campaign.closeout import campaign_publication_report
from ethos.normalization.core import string_sequence
from ethos.repository.context import is_product_root
from ethos.repository.evidence.core import AdapterProofResult
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from ethos.repository.evidence.core import provenance_envelope
from ethos.repository.evidence.core import trim_output
from ethos.repository.policy.gates import adopter_code_correctness_gaps
from ethos.repository.policy.gates import default_gate_ids
from ethos.repository.policy.gates import gate_registry
from ethos.result import EthosResult
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root

if TYPE_CHECKING:
    from pathlib import Path
KNOWN_PROOF_SCOPES = frozenset(
    {"repository", "change", "proof-kernel", "code", "docs", "openspec", "quality"}
)


@dataclass(frozen=True, slots=True)
class _ProofOptions:
    objective: str = "ethos proof"
    scope: str = "repository"
    execute: bool = False
    gate: tuple[str, ...] = ()
    full: bool = False
    change: str | None = None
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    host: bool = False
    probe: bool = False


_DEFAULT_PROOF_OPTIONS = _ProofOptions()


def missing_gate_dependency_next_actions(
    *,
    selected_gate_ids: tuple[str, ...],
    validation_gaps: tuple[str, ...],
    current_head: str,
    root: Path | None = None,
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
    registry = gate_registry(root)
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
        "semantics": "repository is terminal readiness; other scopes are focused evidence",
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
    options: Annotated[_ProofOptions, Parameter(name="*")] = _DEFAULT_PROOF_OPTIONS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Produce a local proof-readiness summary."""
    repo = resolve_root(root)
    current_head = git.current_head(repo)
    audit = status_domain.audit_for_root(
        repo, openspec_mode="deep" if options.full else "shape", current_head=current_head
    )
    changed_paths = change_scope_paths_from_status(
        repo, workspace_status(repo, include_foreign_path_scope=False)
    )
    openspec_lifecycle = openspec_governance_report(
        repo,
        change=options.change,
        lifecycle=True,
        changed_paths=changed_paths,
        require_workspace=False,
    )
    lifecycle_gaps = tuple(str(gap) for gap in openspec_lifecycle.get("required_gaps", []))
    gate_ids = options.gate or (
        default_gate_ids(full=True, root=repo, tree_ref=current_head) if options.full else ()
    )
    try:
        plan = proof_plan(
            repo,
            head=current_head,
            change_id=options.change,
            gate_ids=gate_ids,
            changed_paths=changed_paths,
        )
    except ValueError as exc:
        gap = str(exc)
        emit(
            EthosResult(
                command="prove",
                ok=False,
                state="gapped",
                required_gaps=(gap,),
                next_actions=("ethos adopt",),
            ),
            json_output=json_output,
        )
        return
    plan_gaps = plan.gaps()
    if plan.verdict != "pass":
        emit(
            EthosResult(
                command="prove",
                ok=False,
                state="gapped",
                required_gaps=plan_gaps or ("plan_not_admitted",),
                next_actions=("repair the ChangeContract or repository facts",),
            ),
            json_output=json_output,
        )
        return
    correctness_gaps = adopter_code_correctness_gaps(repo)
    gates_by_id = gate_registry(repo)
    runner = LocalGateRunner() if options.execute else DryRunRunner()
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
        for run_result in (
            runner.run(node, gates_by_id[node.id], root=repo) for node in plan.ordered_nodes()
        )
    )
    evidence = EvidenceSet.from_runs(
        evidence_id=f"ethos:{options.objective}",
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
        if options.execute
        else all(run.state == "planned" for run in proof_runs)
    )
    failed_gate_gaps: tuple[str, ...] = (
        tuple(f"gate_failed:{run.action_id}" for run in proof_runs if run.verdict != "passed")
        if options.execute
        else ()
    )
    proof_gaps: tuple[str, ...] = (
        ("full_proof_requires_execute",) if options.full and not options.execute else ()
    )
    trust_gaps: tuple[str, ...] = (
        ("trust_bearing_proof_missing",)
        if options.execute and verdicts_ok and (not trust_bearing_ok)
        else ()
    )
    head_gaps: tuple[str, ...] = (
        ("expected_head_mismatch",)
        if options.expect_head is not None and options.expect_head != current_head
        else ()
    )
    scope_binding = proof_scope_binding(options.scope)
    scope_gaps = tuple(cast("list[str]", scope_binding["required_gaps"]))
    host_probe = host_probe_boundary(host=options.host, probe=options.probe)
    focused = bool(options.gate) or scope_binding["scope"] != "repository"
    terminal_gaps = (
        tuple(string_sequence(campaign_publication_report(repo).get("required_gaps")))
        if is_product_root(repo) and not focused
        else ()
    )
    required_gaps = tuple(
        dict.fromkeys(
            tuple(string_sequence(audit.get("required_gaps")))
            + lifecycle_gaps
            + plan_gaps
            + correctness_gaps
            + failed_gate_gaps
            + proof_gaps
            + trust_gaps
            + head_gaps
            + scope_gaps
            + terminal_gaps
        )
    )
    ok = (
        bool(audit["ok"])
        and bool(openspec_lifecycle.get("ok"))
        and runs_ok
        and not plan_gaps
        and not required_gaps
    )
    result_state = "proven" if ok and options.execute else "ready" if ok else "gapped"
    if result_state == "proven" and plan.verdict == "pass":
        record_executed_proof(repo, evidence.to_dict(), plan=plan)
    dependency_next_actions = missing_gate_dependency_next_actions(
        selected_gate_ids=options.gate,
        validation_gaps=plan_gaps,
        current_head=current_head,
        root=repo,
    )
    next_actions = dependency_next_actions or (
        ("ethos prove --json",)
        if focused and result_state == "proven"
        else ("ethos land",)
        if result_state == "proven"
        else ("ethos prove --execute",)
        if result_state == "ready"
        else ("ethos campaign status --json",)
        if terminal_gaps
        else ("ethos audit --mode deep",)
    )
    detailed = options.execute or bool(options.gate) or options.full
    boundary = "focused" if focused else "repository"
    audit_openspec = cast("dict[str, object]", audit.get("openspec") or {})
    lifecycle_summary = cast("dict[str, object]", openspec_lifecycle.get("summary") or {})
    lifecycle_change_count = lifecycle_summary.get("change_count")
    data = (
        {
            "governance_context": audit["governance_context"],
            "repository_audit": audit,
            "openspec_lifecycle": openspec_lifecycle,
            "changed_paths": list(changed_paths),
            "executed": options.execute,
            "boundary": boundary,
            "scope": scope_binding["scope"],
            "scope_binding": scope_binding,
            "host_probe": host_probe,
            "plan_ir": plan.to_dict(),
            "evidence": evidence.to_dict(),
            "provenance": provenance_envelope(evidence),
            "expected_head": {
                "expected": options.expect_head or "",
                "current": current_head,
                "ok": options.expect_head is None or options.expect_head == current_head,
            },
        }
        if detailed
        else {
            "executed": options.execute,
            "boundary": boundary,
            "scope": scope_binding["scope"],
            "scope_binding": scope_binding,
            "host_probe": host_probe,
            "gate_ids": [run.action_id for run in proof_runs],
            "changed_path_count": len(changed_paths),
            "audit": {
                "ok": bool(audit.get("ok")),
                "mode": str(audit.get("mode") or ""),
                "openspec_mode": str(audit_openspec.get("mode") or ""),
                "required_gap_count": len(string_sequence(audit.get("required_gaps"))),
            },
            "openspec_lifecycle": {
                "ok": bool(openspec_lifecycle.get("ok")),
                "change": str(openspec_lifecycle.get("change") or ""),
                "schema_name": str(openspec_lifecycle.get("schema_name") or ""),
                "change_count": (
                    lifecycle_change_count if isinstance(lifecycle_change_count, int) else 0
                ),
                "required_gaps": list(string_sequence(openspec_lifecycle.get("required_gaps"))),
            },
            "evidence": {
                "id": evidence.id,
                "head": evidence.head,
                "digest": evidence.digest,
                "durability": evidence.durability,
                "runs": [
                    {
                        "action_id": run.action_id,
                        "state": run.state,
                        "verdict": run.verdict,
                        "evidence_class": run.evidence_class,
                        "trust_bearing": run.trust_bearing,
                    }
                    for run in proof_runs
                ],
            },
            "expected_head": {
                "expected": options.expect_head or "",
                "current": current_head,
                "ok": options.expect_head is None or options.expect_head == current_head,
            },
        }
    )
    result = EthosResult(
        command="prove",
        ok=ok,
        state=result_state,
        summary={
            "objective": options.objective,
            "boundary": boundary,
            "evidence_digest": evidence.digest,
            "gate_count": len(proof_runs),
        },
        required_gaps=required_gaps,
        next_actions=next_actions,
        governance_context=cast("dict[str, object]", audit["governance_context"]),
        data=data,
    )
    emit(result, json_output=json_output)
