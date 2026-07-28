"""Root proof command and proof-scope helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Literal
from typing import cast

from cyclopts import Parameter

import ethos.adapters.repo.git as git
import ethos.domain.status as status_domain
from ethos.adapters.gates.runner import DryRunRunner
from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.mutation.attestation_projection import attestation_payload
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.gates import adopter_code_correctness_gaps
from ethos.repository.policy.gates import default_gate_ids
from ethos.repository.policy.gates import gate_registry
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan
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


def _terminal_check_verdict(adapter_state: str) -> str:
    if adapter_state == "passed":
        return "pass"
    if adapter_state == "failed":
        return "block"
    return "unknown"


def _run_plan_checks(
    *, repo: Path, plan: TransitionPlan, execute: bool
) -> tuple[list[dict[str, object]], bool]:
    """Run or project the admitted TransitionPlan gate sequence."""
    gates_by_id = gate_registry(repo)
    runner = LocalGateRunner() if execute else DryRunRunner()
    checks: list[dict[str, object]] = []
    adapter_states: list[str] = []
    for run_result in (
        runner.run(node, gates_by_id[node.id], root=repo) for node in plan.ordered_nodes()
    ):
        gate = gates_by_id[run_result.action_id]
        adapter_states.append(run_result.state)
        checks.append(
            {
                "action_id": run_result.action_id,
                "command": list(run_result.command),
                "exit_code": run_result.exit_code,
                "stdout": run_result.stdout,
                "stderr": run_result.stderr,
                "verdict": _terminal_check_verdict(run_result.state),
                "evidence_class": gate.evidence_class,
                "trust_bearing": gate.trust_bearing,
                "diagnostics": list(run_result.diagnostics),
            }
        )
    verdicts_ok = bool(checks) and all(check["verdict"] == "pass" for check in checks)
    trust_bearing_ok = any(
        check["trust_bearing"] is True and check["verdict"] == "pass" for check in checks
    )
    runs_ok = (
        verdicts_ok and trust_bearing_ok
        if execute
        else all(state == "planned" for state in adapter_states)
    )
    return checks, runs_ok


def _check_summaries(checks: list[dict[str, object]]) -> list[dict[str, object]]:
    """Project proof checks without embedding diagnostic payloads in command output."""
    return [
        {
            "action_id": check["action_id"],
            "command": check["command"],
            "exit_code": check["exit_code"],
            "verdict": check["verdict"],
            "evidence_class": check["evidence_class"],
            "trust_bearing": check["trust_bearing"],
            "diagnostic_count": len(cast("list[object]", check["diagnostics"])),
        }
        for check in checks
    ]


def _proof_next_actions(
    *,
    options: _ProofOptions,
    plan_gaps: tuple[str, ...],
    current_head: str,
    repo: Path,
    result_state: str,
) -> tuple[str, ...]:
    """Return the next public lifecycle command for one proof outcome."""
    dependency_actions = missing_gate_dependency_next_actions(
        selected_gate_ids=options.gate,
        validation_gaps=plan_gaps,
        current_head=current_head,
        root=repo,
    )
    if dependency_actions:
        return dependency_actions
    if result_state == "proven":
        focused = bool(options.gate) or proof_scope_binding(options.scope)["scope"] != "repository"
        return ("ethos prove --json",) if focused else ("ethos land",)
    if result_state == "ready":
        return ("ethos prove --execute",)
    return ("ethos plan --changed --json",)


@app.command
def prove(
    options: Annotated[_ProofOptions, Parameter(name="*")] = _DEFAULT_PROOF_OPTIONS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Produce proof readiness or one executed generic proof Attestation."""
    repo = resolve_root(root)
    current_head = git.current_head(repo)
    audit = status_domain.audit_for_root(repo, openspec_mode="deep" if options.full else "shape")
    changed_paths = change_scope_paths_from_status(
        repo, workspace_status(repo, include_foreign_path_scope=False)
    )
    openspec_lifecycle = (
        openspec_governance_report(
            repo,
            change=options.change,
            lifecycle=True,
            changed_paths=changed_paths,
            require_workspace=False,
        )
        if openspec_profile_enabled(repo, tree_ref=current_head)
        else {"ok": True, "state": "not_applicable", "required_gaps": []}
    )
    try:
        plan = proof_plan(
            repo,
            head=current_head,
            change_id=options.change,
            gate_ids=(
                options.gate
                or (
                    default_gate_ids(full=True, root=repo, tree_ref=current_head)
                    if options.full
                    else ()
                )
            ),
            changed_paths=changed_paths,
        )
    except ValueError as exc:
        emit(
            EthosResult(
                command="prove",
                ok=False,
                state="gapped",
                required_gaps=(str(exc),),
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
                next_actions=("repair the Commitment or repository facts",),
            ),
            json_output=json_output,
        )
        return
    checks, runs_ok = _run_plan_checks(repo=repo, plan=plan, execute=options.execute)
    verdicts_ok = bool(checks) and all(check["verdict"] == "pass" for check in checks)
    trust_bearing_ok = any(
        check["trust_bearing"] is True and check["verdict"] == "pass" for check in checks
    )
    failed_gate_gaps: tuple[str, ...] = (
        tuple(
            (
                f"gate_failed:{check['action_id']}"
                if check["verdict"] == "block"
                else f"gate_unknown:{check['action_id']}"
            )
            for check in checks
            if check["verdict"] != "pass"
        )
        if options.execute
        else ()
    )
    trust_gaps: tuple[str, ...] = (
        ("trust_bearing_proof_missing",)
        if options.execute and verdicts_ok and not trust_bearing_ok
        else ()
    )
    scope_binding = proof_scope_binding(options.scope)
    host_probe = host_probe_boundary(host=options.host, probe=options.probe)
    focused = bool(options.gate) or scope_binding["scope"] != "repository"
    required_gaps = tuple(
        dict.fromkeys(
            tuple(string_sequence(audit.get("required_gaps")))
            + tuple(str(gap) for gap in openspec_lifecycle.get("required_gaps", []))
            + plan_gaps
            + tuple(adopter_code_correctness_gaps(repo))
            + failed_gate_gaps
            + (("full_proof_requires_execute",) if options.full and not options.execute else ())
            + trust_gaps
            + (
                ("expected_head_mismatch",)
                if options.expect_head is not None and options.expect_head != current_head
                else ()
            )
            + tuple(cast("list[str]", scope_binding["required_gaps"]))
        )
    )
    ok = (
        bool(audit["ok"])
        and bool(openspec_lifecycle.get("ok"))
        and runs_ok
        and not plan_gaps
        and not required_gaps
    )
    boundary = "focused" if focused else "repository"
    attestation = None
    if options.execute:
        verdict: Literal["pass", "block", "unknown"] = (
            "block" if required_gaps else "pass" if ok else "unknown"
        )
        attestation = issue_proof_attestation(
            repo,
            {
                "plan": plan,
                "checks": tuple(checks),
                "verdict": verdict,
                "issuer": os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos",
                "scope": str(scope_binding["scope"]),
                "boundary": boundary,
                "objective": options.objective,
                "required_gaps": required_gaps,
            },
        )
        if attestation.verdict == "pass":
            try:
                persist_proof_attestation(repo, attestation)
            except ValueError as error:
                required_gaps = tuple(
                    dict.fromkeys((*required_gaps, f"proof_attestation_persistence_failed:{error}"))
                )
                ok = False
                attestation = issue_proof_attestation(
                    repo,
                    {
                        "plan": plan,
                        "checks": tuple(checks),
                        "verdict": "block",
                        "issuer": os.environ.get("ETHOS_ACTOR", "").strip()
                        or "agent:local:process:ethos",
                        "scope": str(scope_binding["scope"]),
                        "boundary": boundary,
                        "objective": options.objective,
                        "required_gaps": required_gaps,
                    },
                )
    result_state = "proven" if ok and options.execute else "ready" if ok else "gapped"
    next_actions = _proof_next_actions(
        options=options,
        plan_gaps=plan_gaps,
        current_head=current_head,
        repo=repo,
        result_state=result_state,
    )
    detailed = options.execute or bool(options.gate) or options.full
    audit_openspec = cast("dict[str, object]", audit.get("openspec") or {})
    lifecycle_summary = cast("dict[str, object]", openspec_lifecycle.get("summary") or {})
    lifecycle_change_count = lifecycle_summary.get("change_count")
    check_summaries = _check_summaries(checks)
    attestation_projection = (
        attestation_payload(attestation, kind="proof") if attestation is not None else {}
    )
    artifact = attestation.statement.get("artifact") if attestation is not None else {}
    artifact_reference = dict(artifact) if isinstance(artifact, Mapping) else {}
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
            "transition_plan": plan.to_dict(),
            "attestation": attestation_projection,
            "artifact_reference": artifact_reference,
            "checks": check_summaries,
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
            "gate_ids": [check["action_id"] for check in checks],
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
            "attestation": attestation_projection,
            "artifact_reference": artifact_reference,
            "checks": check_summaries,
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
            "attestation_id": attestation.id if attestation is not None else "",
            "gate_count": len(checks),
        },
        required_gaps=required_gaps,
        next_actions=next_actions,
        governance_context=cast("dict[str, object]", audit["governance_context"]),
        data=data,
    )
    emit(result, json_output=json_output)
