"""Root proof command and proof-scope helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Annotated
from typing import cast

from cyclopts import Parameter

import ethos.adapters.repo.git as git
import ethos.domain.status as status_domain
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import CurrentScope
from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.adapters.gates.runner import DryRunRunner
from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.gates.runner import run_gate_waves
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.status.workspace import workspace_status_observation
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import observation_verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Attestation
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


def proof_scope_binding(scope: str) -> dict[str, object]:
    """Return the proof-scope binding for command payloads."""
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


def _host_gate_observation(
    *, repo: Path, gate_ids: tuple[str, ...], expect_head: str | None
) -> EthosResult:
    """Execute focused gates without repository lifecycle or Attestation authority."""
    current_head = git.current_head(repo)
    required_gaps = (
        ("host_gate_selection_required",)
        if not gate_ids
        else ("expected_head_mismatch",)
        if expect_head is not None and expect_head != current_head
        else ()
    )
    checks: list[dict[str, object]] = []
    if not required_gaps:
        policy = resolve_gate_policy(repo, tree_ref=current_head, gate_ids=gate_ids)
        results = run_gate_waves(
            LocalGateRunner(),
            policy.nodes,
            policy.registry,
            root=repo,
            capacity=max(1, os.cpu_count() or 1),
            parallel=True,
        )
        checks = [
            {
                "action_id": result.action_id,
                "command": list(result.command),
                "exit_code": result.exit_code,
                "verdict": result.verdict,
                "diagnostics": list(result.diagnostics),
            }
            for result in results
        ]
        required_gaps = tuple(
            f"gate_{'failed' if check['verdict'] == 'block' else 'unknown'}:{check['action_id']}"
            for check in checks
            if check["verdict"] != "pass"
        )
    verdict: Verdict = "pass" if checks and not required_gaps else "block"
    return EthosResult(
        command="prove",
        verdict=verdict,
        state="observed" if verdict == "pass" else "gapped",
        summary={
            "boundary": "host",
            "gate_count": len(checks),
            "proof_attestation_issued": False,
        },
        required_gaps=required_gaps,
        next_action="repair the selected host gate" if required_gaps else "",
        data={
            "executed": True,
            "boundary": "host",
            "host_probe": host_probe_boundary(host=True, probe=False),
            "checks": checks,
            "attestation": {},
            "expected_head": {
                "expected": expect_head or "",
                "current": current_head,
                "matches": expect_head is None or expect_head == current_head,
            },
        },
    )


def _emit_host_gate_observation(*, repo: Path, options: _ProofOptions, json_output: bool) -> bool:
    """Emit the host-only gate result and report whether it owned this invocation."""
    if not (options.host and options.execute):
        return False
    emit(
        _host_gate_observation(
            repo=repo,
            gate_ids=options.gate,
            expect_head=options.expect_head,
        ),
        json_output=json_output,
    )
    return True


def resolve_generation(repo: Path, *, change: str | None = None) -> CurrentResolution | None:
    """Resolve the selected logical Change and current-generation scope."""
    status, authority = workspace_status_observation(repo, include_foreign_path_scope=False)
    try:
        return resolve_current_resolution(
            repo,
            status=status,
            authority=authority,
            change=change,
            changed=True,
        )
    except ValueError:
        return None


def resolve_generation_scope(repo: Path) -> CurrentScope:
    """Observe one current Change generation scope for this proof invocation."""
    generation = resolve_generation(repo)
    return (
        generation.scope
        if generation is not None
        else CurrentScope((), gaps=("change_generation_binding_invalid",))
    )


def _proof_context(
    repo: Path, options: _ProofOptions
) -> tuple[str, dict[str, object], CurrentResolution | None, dict[str, object]]:
    """Observe the repository and OpenSpec lifecycle once for governed proof."""
    current_head = git.current_head(repo)
    audit = status_domain.audit_for_root(repo, openspec_mode="deep" if options.full else "shape")
    generation = resolve_generation(repo, change=options.change)
    openspec_lifecycle: dict[str, object] = (
        dict(generation.openspec)
        if generation is not None and generation.openspec
        else {"verdict": "pass", "state": "not_applicable", "required_gaps": []}
    )
    return current_head, audit, generation, openspec_lifecycle


def run_plan_checks(
    *,
    repo: Path,
    plan: TransitionPlan,
    execute: bool,
    capacity: int | None = None,
) -> tuple[list[dict[str, object]], bool]:
    """Run or project the admitted TransitionPlan gate sequence."""
    plan_head = plan.facts.get("head")
    if not isinstance(plan_head, str) or not plan_head:
        message = "proof_plan_head_missing"
        raise ValueError(message)
    gates_by_id = resolve_gate_policy(
        repo,
        tree_ref=plan_head,
        gate_ids=tuple(node.id for node in plan.nodes),
    ).registry
    runner = LocalGateRunner() if execute else DryRunRunner()
    node_capacity = capacity or max(1, os.cpu_count() or 1)
    results = run_gate_waves(
        runner, plan.nodes, gates_by_id, root=repo, capacity=node_capacity, parallel=execute
    )
    checks: list[dict[str, object]] = []
    for run_result in results:
        gate = gates_by_id[run_result.action_id]
        checks.append(
            {
                "action_id": run_result.action_id,
                "command": list(run_result.command),
                "exit_code": run_result.exit_code,
                "stdout": run_result.stdout,
                "stderr": run_result.stderr,
                "verdict": run_result.verdict,
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
        else bool(checks) and all(check["exit_code"] is None for check in checks)
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


def _proof_next_action(
    *,
    options: _ProofOptions,
    result_state: str,
) -> str:
    """Return the next public lifecycle command for one proof outcome."""
    if result_state == "proven":
        focused = bool(options.gate) or proof_scope_binding(options.scope)["scope"] != "repository"
        return "ethos prove --json" if focused else "ethos land"
    if result_state == "ready":
        return "ethos prove --execute"
    return "ethos plan --changed --json"


def _proof_plan_error_next_action(gap: str) -> str:
    """Resolve one exact public recovery command for plan-construction failure."""
    return "ethos lane status --json" if gap.startswith("lease_") else "ethos adopt"


def _issue_proof_or_emit_gap(
    repo: Path,
    *,
    plan: TransitionPlan,
    checks: list[dict[str, object]],
    verdict: Verdict,
    options: _ProofOptions,
    scope: str,
    boundary: str,
    required_gaps: tuple[str, ...],
    json_output: bool,
) -> Attestation | None:
    """Issue one proof or project its semantic mismatch at the CLI boundary."""
    try:
        return issue_proof_attestation(
            repo,
            {
                "plan": plan,
                "checks": tuple(checks),
                "verdict": verdict,
                "issuer": os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos",
                "scope": scope,
                "boundary": boundary,
                "objective": options.objective,
                "required_gaps": required_gaps,
            },
        )
    except ValueError as error:
        emit(
            EthosResult(
                command="prove",
                verdict="block",
                state="gapped",
                required_gaps=(str(error),),
                next_action="ethos plan --changed --json",
            ),
            json_output=json_output,
        )
        return None


@app.command
def prove(
    options: Annotated[_ProofOptions, Parameter(name="*")] = _DEFAULT_PROOF_OPTIONS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Produce proof readiness or one executed generic proof Attestation."""
    repo = resolve_root(root)
    if _emit_host_gate_observation(repo=repo, options=options, json_output=json_output):
        return
    current_head, audit, generation, openspec_lifecycle = _proof_context(repo, options)
    generation_scope = (
        generation.scope
        if generation is not None
        else CurrentScope((), gaps=("change_generation_binding_invalid",))
    )
    changed_paths = generation_scope.paths
    try:
        plan = proof_plan(
            repo,
            head=current_head,
            change_id=options.change,
            gate_ids=options.gate,
            full=options.full,
            changed_paths=generation_scope.paths,
            generation_binding=generation,
        )
    except ValueError as exc:
        emit(
            EthosResult(
                command="prove",
                verdict="block",
                state="gapped",
                required_gaps=(str(exc),),
                next_action=_proof_plan_error_next_action(str(exc)),
            ),
            json_output=json_output,
        )
        return
    plan_gaps = plan.required_gaps
    if plan.verdict != "pass":
        emit(
            EthosResult(
                command="prove",
                verdict=plan.verdict,
                state="gapped",
                required_gaps=plan_gaps or ("plan_not_admitted",),
                next_action="repair the Commitment or repository facts",
            ),
            json_output=json_output,
        )
        return
    try:
        checks, runs_ok = run_plan_checks(repo=repo, plan=plan, execute=options.execute)
    except ValueError as exc:
        emit(
            EthosResult(
                command="prove",
                verdict="block",
                state="gapped",
                required_gaps=(str(exc),),
                next_action="ethos plan --changed --json",
            ),
            json_output=json_output,
        )
        return
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
    scope_binding, host_probe = (
        proof_scope_binding(options.scope),
        host_probe_boundary(host=options.host, probe=options.probe),
    )
    focused = bool(options.gate) or scope_binding["scope"] != "repository"
    required_gaps = tuple(
        dict.fromkeys(
            tuple(string_sequence(audit.get("required_gaps")))
            + tuple(string_sequence(openspec_lifecycle.get("required_gaps")))
            + plan_gaps
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
    check_verdict: Verdict = (
        reduce_verdicts(*(cast("Verdict", check["verdict"]) for check in checks))
        if options.execute and checks
        else observation_verdict(ok=runs_ok)
        if checks
        else "unknown"
    )
    verdict = reduce_verdicts(
        report_verdict(audit),
        report_verdict(openspec_lifecycle),
        plan.verdict,
        check_verdict,
        required_gaps=required_gaps,
    )
    boundary = "focused" if focused else "repository"
    attestation = (
        _issue_proof_or_emit_gap(
            repo,
            plan=plan,
            checks=checks,
            verdict=verdict,
            options=options,
            scope=str(scope_binding["scope"]),
            boundary=boundary,
            required_gaps=required_gaps,
            json_output=json_output,
        )
        if options.execute
        else None
    )
    if options.execute and attestation is None:
        return
    if attestation is not None and attestation.verdict == "pass":
        try:
            persist_proof_attestation(repo, attestation)
        except ValueError as error:
            required_gaps = tuple(
                dict.fromkeys((*required_gaps, f"proof_attestation_persistence_failed:{error}"))
            )
            verdict = "block"
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
    result_state = (
        "proven"
        if verdict == "pass" and options.execute
        else "ready"
        if verdict == "pass"
        else "gapped"
    )
    next_action = _proof_next_action(
        options=options,
        result_state=result_state,
    )
    detailed = options.execute or bool(options.gate) or options.full
    audit_openspec = cast("dict[str, object]", audit.get("openspec") or {})
    lifecycle_summary = cast("dict[str, object]", openspec_lifecycle.get("summary") or {})
    lifecycle_change_count = lifecycle_summary.get("change_count")
    check_summaries = _check_summaries(checks)
    attestation_data = attestation.model_dump(mode="json") if attestation is not None else {}
    artifact = attestation.payload.body.get("artifact") if attestation is not None else {}
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
            "transition_plan": plan.model_dump(mode="json"),
            "attestation": attestation_data,
            "artifact_reference": artifact_reference,
            "checks": check_summaries,
            "expected_head": {
                "expected": options.expect_head or "",
                "current": current_head,
                "matches": options.expect_head is None or options.expect_head == current_head,
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
                "verdict": report_verdict(audit),
                "mode": str(audit.get("mode") or ""),
                "openspec_mode": str(audit_openspec.get("mode") or ""),
                "required_gap_count": len(string_sequence(audit.get("required_gaps"))),
            },
            "openspec_lifecycle": {
                "verdict": report_verdict(openspec_lifecycle),
                "change": str(openspec_lifecycle.get("change") or ""),
                "schema_name": str(openspec_lifecycle.get("schema_name") or ""),
                "change_count": (
                    lifecycle_change_count if isinstance(lifecycle_change_count, int) else 0
                ),
                "required_gaps": list(string_sequence(openspec_lifecycle.get("required_gaps"))),
            },
            "attestation": attestation_data,
            "artifact_reference": artifact_reference,
            "checks": check_summaries,
            "expected_head": {
                "expected": options.expect_head or "",
                "current": current_head,
                "matches": options.expect_head is None or options.expect_head == current_head,
            },
        }
    )
    result = EthosResult(
        command="prove",
        verdict=verdict,
        state=result_state,
        summary={
            "objective": options.objective,
            "boundary": boundary,
            "attestation_id": attestation.id if attestation is not None else "",
            "gate_count": len(checks),
        },
        required_gaps=required_gaps,
        next_action=next_action,
        governance_context=cast("dict[str, object]", audit["governance_context"]),
        data=data,
    )
    emit(result, json_output=json_output)
