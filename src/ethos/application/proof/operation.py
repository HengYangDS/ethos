"""Plan, run and attest one repository proof as an application operation."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from contextlib import contextmanager
from contextlib import nullcontext
from dataclasses import asdict
from time import monotonic
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.remediation.guidance as remediation
import ethos.domain.status as status_domain
from ethos.adapters.actor import process_issuer
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.adapters.gates.proof_slot import STALE
from ethos.adapters.gates.proof_slot import admitted_full_proof
from ethos.adapters.gates.runner import DryRunRunner
from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.gates.runner import readiness_tier
from ethos.adapters.gates.runner import run_gate_graph
from ethos.adapters.mutation.proof import assert_proof_execution_source
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.mutation.proof_validation import assess_proof_execution
from ethos.adapters.mutation.proof_validation import expected_head_gaps
from ethos.adapters.openspec.selection import selected_change
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.status.workspace import workspace_status_observation
from ethos.application.catalog import invoke
from ethos.application.proof.host import host_gate_observation
from ethos.application.proof.host import host_probe_boundary
from ethos.application.proof.host import readiness_observation
from ethos.application.proof.report import compact_proof_context
from ethos.application.proof.report import proof_scope_binding
from ethos.application.proof.report import summarize_checks
from ethos.contracts.operations.prove import ProofRequest
from ethos.contracts.outcome import outcome_of
from ethos.contracts.proof.plan import proof_acceptance_purpose
from ethos.contracts.verdict import execution_succeeded
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.paradigm.parameters import active_resolution
from ethos.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator
    from contextlib import AbstractContextManager
    from pathlib import Path

    from ethos.adapters.gates.proof_slot import SlotAdmission
    from ethos.adapters.gates.runner import ActionRunResult
    from ethos.contracts.plan import PlanNode
    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Attestation
    from ethos.contracts.verdict import Verdict


_DEFAULT_REQUEST = ProofRequest()


def _proof_preflight(*, options: ProofRequest) -> EthosResult | None:
    """Refuse a local-source proof that is not one full repository proof."""
    if options.acceptance_purpose == "local-source" and (
        options.host
        or options.probe
        or options.scope != "repository"
        or options.gate
        or not options.full
    ):
        return _proof_gap(ValueError("local_source_proof_requires_full_repository"))
    return None


def _proof_context(
    repo: Path, options: ProofRequest
) -> tuple[str, dict[str, object], CurrentResolution, dict[str, object]]:
    """Observe the repository and OpenSpec lifecycle once for governed proof."""
    status, authority = workspace_status_observation(repo, include_foreign_path_scope=False)
    resolution = resolve_current_resolution(
        repo,
        status=status,
        authority=authority,
        change=options.change,
        changed=True,
    )
    current_head = resolution.authority.current_head if resolution.authority is not None else ""
    openspec_lifecycle: dict[str, object] = (
        dict(resolution.openspec)
        if resolution.openspec
        else {"verdict": "pass", "state": "not_applicable", "required_gaps": []}
    )
    audit = status_domain.audit_for_root(
        repo, openspec=openspec_lifecycle if options.full else None
    )
    return current_head, audit, resolution, openspec_lifecycle


def _gate_progress(
    plan: TransitionPlan, action_id: str, result: ActionRunResult | None = None
) -> None:
    """Flush diagnostic execution events without turning them into proof evidence."""
    event: dict[str, object] = {
        "event": "gate_scheduled" if result is None else "gate_completed",
        "head": plan.facts["head"],
        "plan_digest": plan.digest,
        "action_id": action_id,
        "satisfies_repository_proof": False,
    }
    if result is not None:
        event.update(
            verdict=result.verdict,
            exit_code=result.exit_code,
            started_after_seconds=result.started_after_seconds,
            duration_seconds=result.duration_seconds,
            timeout_seconds=result.timeout_seconds,
            timeout_source=result.timeout_source,
            diagnostics=list(result.diagnostics),
        )
        if result.verdict != "pass":
            event.update(stdout=result.stdout, stderr=result.stderr)
    sys.stderr.write(json.dumps(event, sort_keys=True, default=str) + "\n")
    sys.stderr.flush()


def run_plan_checks(
    *,
    repo: Path,
    plan: TransitionPlan,
    execute: bool,
    capacity: int | None = None,
    admission: Callable[[], AbstractContextManager[object]] | None = None,
) -> tuple[list[dict[str, object]], bool]:
    """Run or project the admitted TransitionPlan gate sequence.

    With an admission scope, the readiness tier runs first and the other gates run inside the
    scope; when a readiness gate fails, or no other gate is planned, the scope is never entered.
    """
    plan_head = plan.facts.get("head")
    if not isinstance(plan_head, str) or not plan_head:
        message = "proof_plan_head_missing"
        raise ValueError(message)
    if execute:
        assert_proof_execution_source(repo, plan)
    gates_by_id = resolve_gate_policy(
        repo,
        tree_ref=plan_head,
        gate_ids=tuple(node.id for node in plan.nodes),
        acceptance_purpose=proof_acceptance_purpose(plan.policy),
    )
    registry = gates_by_id.registry
    runner = LocalGateRunner() if execute else DryRunRunner()
    node_capacity = capacity or max(1, os.cpu_count() or 1)
    epoch = monotonic()

    def graph(
        nodes: tuple[PlanNode, ...], settled: Mapping[str, ActionRunResult] | None = None
    ) -> tuple[ActionRunResult, ...]:
        return run_gate_graph(
            runner,
            nodes,
            registry,
            root=repo,
            capacity=node_capacity,
            parallel=execute,
            on_schedule=(lambda action_id: _gate_progress(plan, action_id)) if execute else None,
            on_result=(lambda result: _gate_progress(plan, result.action_id, result))
            if execute
            else None,
            settled=settled,
            epoch=epoch,
        )

    if admission is None:
        results = graph(plan.nodes)
    else:
        tier = set(readiness_tier(plan.nodes, registry))
        readiness = graph(tuple(node for node in plan.nodes if node.id in tier))
        ready = all(execution_succeeded(asdict(result)) for result in readiness)
        # Admission protects the gates that follow readiness; a plan without any never waits.
        remaining = any(node.id not in tier for node in plan.nodes)
        with admission() if ready and remaining else nullcontext():
            results = graph(plan.nodes, {result.action_id: result for result in readiness})
    checks: list[dict[str, object]] = []
    for run_result in results:
        gate = registry[run_result.action_id]
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
                **(
                    {"verification": run_result.verification}
                    if run_result.verification is not None
                    else {}
                ),
                "started_after_seconds": run_result.started_after_seconds,
                "duration_seconds": run_result.duration_seconds,
            }
        )
    if execute:
        assert_proof_execution_source(repo, plan, checks=tuple(checks))
    verdicts_ok = bool(checks) and all(execution_succeeded(check) for check in checks)
    trust_bearing_ok = any(
        check["trust_bearing"] is True and check["verdict"] == "pass" for check in checks
    )
    runs_ok = (
        verdicts_ok and trust_bearing_ok
        if execute
        else bool(checks) and all(check["exit_code"] is None for check in checks)
    )
    return checks, runs_ok


def _admitted_plan(
    repo: Path, resolution: CurrentResolution, options: ProofRequest
) -> TransitionPlan | EthosResult:
    """Return the admitted TransitionPlan, or the refusal that stops the proof before any gate."""
    try:
        plan = proof_plan(
            repo,
            resolution=resolution,
            gate_ids=options.gate,
            full=options.full,
            acceptance_purpose=getattr(options, "acceptance_purpose", "repository"),
        )
    except ValueError as exc:
        return _proof_gap(exc)
    if plan.verdict != "pass":
        return EthosResult(
            command="prove",
            verdict=plan.verdict,
            state="gapped",
            required_gaps=plan.required_gaps or ("plan_not_admitted",),
            next_action=_plan_next_action(options.gate, plan.required_gaps),
        )
    return plan


def _plan_next_action(gate: tuple[str, ...], gaps: tuple[str, ...]) -> str:
    """Route a focused plan refused only for axes it did not select to the full proof."""
    if gate and gaps and all(gap.startswith("quality_obligation_unproven:") for gap in gaps):
        return "ethos prove --execute --json"
    return "repair the Commitment or repository facts"


def _proof_next_action(
    *,
    options: ProofRequest,
    result_state: str,
    gaps: tuple[str, ...] = (),
) -> str:
    """Return the next public lifecycle command for one proof outcome."""
    if result_state == "proven":
        focused = bool(options.gate) or proof_scope_binding(options.scope)["scope"] != "repository"
        return "ethos prove --json" if focused else "ethos land"
    if result_state == "ready":
        return "ethos prove --execute"
    return _gap_remedy(gaps) or "ethos plan --changed --json"


def _gap_remedy(gaps: tuple[str, ...]) -> str:
    """Return the first remedy that the gaps' owner declares, if any."""
    return next((str(hint["next_action"]) for hint in remediation.remediation_for_gaps(gaps)), "")


def _proof_gap(error: ValueError, *, head: str = "") -> EthosResult:
    """Project one proof failure with its carried verdict, causes and evidence, and no claim."""
    outcome = outcome_of(error)
    refresh = f"ethos lane refresh-base --apply --authorize --expect-head {head} --json"
    return EthosResult.from_outcome(
        "prove",
        outcome,
        state="gapped",
        next_action=refresh if outcome.gaps == (STALE,) else _gap_remedy(outcome.gaps),
        fallback="ethos plan --changed --json",
        data=getattr(error, "observation", {}),
    )


def _apply_proof_effect(
    repo: Path,
    payload: Mapping[str, object],
    *,
    execute: bool,
    verdict: Verdict,
    required_gaps: tuple[str, ...],
) -> tuple[Attestation | None, Verdict, tuple[str, ...], EthosResult | None]:
    """Issue and select one proof, or return the single failed effect boundary."""
    if not execute:
        return None, verdict, required_gaps, None
    try:
        attestation = issue_proof_attestation(repo, payload)
        if attestation.verdict == "pass":
            try:
                persist_proof_attestation(repo, attestation)
            except ValueError as error:
                failed = (
                    f"proof_attestation_persistence_failed:{gap}" for gap in outcome_of(error).gaps
                )
                required_gaps = tuple(dict.fromkeys((*required_gaps, *failed)))
                verdict = "block"
                attestation = issue_proof_attestation(
                    repo,
                    {**payload, "verdict": verdict, "required_gaps": required_gaps},
                )
    except ValueError as error:
        return None, verdict, required_gaps, _proof_gap(error)
    return attestation, verdict, required_gaps, None


def prove_repository(root: Path, request: ProofRequest = _DEFAULT_REQUEST) -> EthosResult:
    """Produce proof readiness or one executed generic proof Attestation."""
    return invoke("prove", root, request)


def prove_governed(root: Path, request: ProofRequest) -> EthosResult:
    """Run `proof.preview`, `proof.execute` and `proof.run`; only `invoke` calls it."""
    with selected_change(request.change):
        return _prove(root.resolve(), request)


def prove_readiness(root: Path, request: ProofRequest) -> EthosResult:
    """Run `proof.readiness`; only `invoke` calls it."""
    with selected_change(request.change):
        return readiness_observation(repo=root.resolve(), expect_head=request.expect_head)


def prove_on_host(root: Path, request: ProofRequest) -> EthosResult:
    """Run `proof.host`; only `invoke` calls it."""
    with selected_change(request.change):
        return host_gate_observation(
            repo=root.resolve(),
            gate_ids=request.gate,
            expect_head=request.expect_head,
            full=request.full,
        )


def _prove(repo: Path, options: ProofRequest) -> EthosResult:
    preflight = _proof_preflight(options=options)
    if preflight is not None:
        return preflight
    current_head, audit, resolution, openspec_lifecycle = _proof_context(repo, options)
    audit_verdict = report_verdict(audit)
    head_gaps = (
        expected_head_gaps(options.expect_head, current_head)
        if options.execute and resolution.verdict == "pass" and audit_verdict == "pass"
        else ()
    )
    if resolution.verdict != "pass" or audit_verdict != "pass" or head_gaps:
        unresolved = resolution.verdict != "pass"
        audit_failed = audit_verdict != "pass"
        audit_gaps = tuple(string_sequence(audit.get("required_gaps"))) or (
            "repository_audit_not_passed",
        )
        return EthosResult(
            command="prove",
            verdict=(
                resolution.verdict if unresolved else audit_verdict if audit_failed else "block"
            ),
            state="gapped",
            required_gaps=(
                resolution.required_gaps
                if unresolved
                else audit_gaps
                if audit_failed
                else head_gaps
            ),
            next_action=(
                resolution.next_action
                if unresolved
                else str(audit.get("next_action") or "repair the reported repository policy")
                if audit_failed
                else "ethos plan --changed --json"
            ),
            user_decision_required=resolution.user_decision_required if unresolved else False,
        )
    changed_paths = resolution.scope.paths
    plan = _admitted_plan(repo, resolution, options)
    if isinstance(plan, EthosResult):
        return plan
    # A full proof runs its readiness gates first, then waits for its repository's slot and host
    # capacity before its test and package gates.
    granted: list[SlotAdmission] = []

    @contextmanager
    def admission() -> Generator[None]:
        with admitted_full_proof(repo, head=current_head) as slot:
            granted.append(slot)
            yield

    try:
        checks, runs_ok = run_plan_checks(
            repo=repo,
            plan=plan,
            execute=options.execute,
            admission=admission if options.execute and options.full else None,
        )
    except ValueError as exc:
        return _proof_gap(exc, head=current_head)
    scope_binding, host_probe = (
        proof_scope_binding(options.scope),
        host_probe_boundary(host=options.host, probe=options.probe),
    )
    focused = bool(options.gate) or scope_binding["scope"] != "repository"
    assessed = assess_proof_execution(
        audit=audit,
        lifecycle=openspec_lifecycle,
        plan=plan,
        checks=checks,
        runs_ok=runs_ok,
        execute=options.execute,
        full=options.full,
        expected_head=options.expect_head,
        current_head=current_head,
        scope_gaps=tuple(cast("list[str]", scope_binding["required_gaps"])),
    )
    verdict, required_gaps = assessed.verdict, assessed.gaps
    boundary = "focused" if focused else "repository"
    payload = {
        "plan": plan,
        "checks": tuple(checks),
        "verdict": verdict,
        "issuer": process_issuer(),
        "scope": str(scope_binding["scope"]),
        "boundary": boundary,
        "objective": options.objective,
        "required_gaps": required_gaps,
    }
    attestation, verdict, required_gaps, stop = _apply_proof_effect(
        repo,
        payload,
        execute=options.execute,
        verdict=verdict,
        required_gaps=required_gaps,
    )
    if stop is not None:
        return stop
    result_state = (
        "proven"
        if verdict == "pass" and options.execute
        else "ready"
        if verdict == "pass"
        else "gapped"
    )
    detailed = options.execute or bool(options.gate) or options.full
    check_summaries = summarize_checks(checks)
    artifact = attestation.payload.body.get("artifact") if attestation is not None else {}
    data = {
        "executed": options.execute,
        "boundary": boundary,
        "scope": scope_binding["scope"],
        "scope_binding": scope_binding,
        "host_probe": host_probe,
        "attestation": attestation.model_dump(mode="json") if attestation is not None else {},
        "artifact_reference": dict(artifact) if isinstance(artifact, Mapping) else {},
        "checks": check_summaries,
        "parameter_deviations": list(active_resolution().deviations),
        "expected_head": {
            "expected": options.expect_head or "",
            "current": current_head,
            "matches": options.expect_head is None or options.expect_head == current_head,
        },
    }
    if granted:
        data["admission"] = asdict(granted[0])
    if detailed:
        data.update(
            governance_context=audit["governance_context"],
            repository_audit=audit,
            openspec_lifecycle=openspec_lifecycle,
            changed_paths=list(changed_paths),
            transition_plan=plan.model_dump(mode="json"),
        )
    else:
        data.update(
            gate_ids=[check["action_id"] for check in checks],
            changed_path_count=len(changed_paths),
            **compact_proof_context(audit, openspec_lifecycle),
        )
    return EthosResult(
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
        diagnostics=assessed.causes,
        next_action=_proof_next_action(
            options=options, result_state=result_state, gaps=required_gaps
        ),
        governance_context=cast("dict[str, object]", audit["governance_context"]),
        data=data,
    )
