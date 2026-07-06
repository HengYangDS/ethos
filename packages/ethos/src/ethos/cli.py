from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from typing import cast

from ethos.adapters.gates import tool as _qtool
from ethos.adapters.gates.runner import DryRunRunner
from ethos.adapters.gates.runner import LocalSubprocessRunner
from ethos.adapters.mutation.core import MutationRequest
from ethos.adapters.mutation.core import apply_candidate_to_accepted
from ethos.adapters.mutation.core import apply_land_to_candidate
from ethos.adapters.mutation.core import candidate_base_report
from ethos.adapters.mutation.core import evaluate_closeout_mutation
from ethos.adapters.mutation.core import evaluate_mutation
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.adapters.openspec import (
    completed_active_changes_report as openspec_completed_active_changes_report,
)
from ethos.adapters.openspec import openspec_governance_report
from ethos.adapters.repo import git as _gitio
from ethos.adapters.repo.status import workspace_status
from ethos.adapters.store.state import initialize_state
from ethos.domain import land as _land
from ethos.domain import orient as _orient
from ethos.domain import plan as _plan
from ethos.domain import prove as _prove
from ethos.domain import status as _status
from ethos.domain.report import scorecard_report
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.evidence.core import AdapterProofResult
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from ethos.repository.evidence.core import provenance_envelope
from ethos.repository.evidence.core import trim_output
from ethos.repository.policy.gates import gate_graph
from ethos.repository.policy.gates import gate_registry
from ethos.repository.registry.docs import build_docs_registry
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import load_command_groups as _load_command_groups
from ethos.surface.cli._base import resolve_root
from ethos.surface.cli._gate_runner import run_inprocess_cli_gate as _run_inprocess_cli_gate
from ethos_core.contracts.branch_roles import load_branch_role_policy

# Command-group modules register their commands onto the shared *_app objects at
# import time; importing them here wires those groups into the CLI. Each group
# imports only its own domain deps, so a group's heavy dependencies load only when
# that group is imported (lazy path for the common commands).
from ethos_core.invalid_states import UNCLASSIFIED
from ethos_core.invalid_states import explain_gap
from ethos_core.result import EthosResult


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def _git_files(root: Path, *patterns: str) -> list[str]:
    return _gitio.git_files(root, *patterns)


def _quality_tool_report(
    *,
    root: Path,
    gate_id: str,
    tool: str,
    command: list[str],
    files: list[str],
) -> dict[str, object]:
    return _qtool.quality_tool_report(
        root=root,
        gate_id=gate_id,
        tool=tool,
        command=command,
        files=files,
    )


def _code_size_report(root: Path) -> dict[str, object]:
    return _prove.code_size_report(root)


def _command_data_validation(
    repo: Path,
    *,
    schema_name: str,
    payload: dict[str, object],
) -> dict[str, object]:
    return _prove.command_data_validation(repo, schema_name=schema_name, payload=payload)


@app.command
def status(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Inspect repository state."""
    repo = resolve_root(root)
    status_payload = workspace_status(repo)
    orientation = _orient.orientation_packet(status_payload=status_payload)
    orientation_actions = cast("list[str]", orientation["next_actions"])
    coordination = cast("dict[str, object]", status_payload.get("coordination", {}))
    validation = _prove.workspace_status_validation(repo, status_payload)
    validation_gaps = _prove.workspace_status_validation_gaps(validation)
    ok = bool(validation["ok"])
    result = EthosResult(
        command="status",
        ok=ok,
        state="invalid" if not ok else "dirty" if status_payload["dirty"] else "ready",
        summary={
            "root": str(repo),
            "branch": status_payload["branch"],
            "role": status_payload["role"],
            "dirty": status_payload["dirty"],
            "changed_path_count": len(cast("list[object]", status_payload["changed_paths"])),
            "foreign_work_lane_count": coordination.get("foreign_work_lane_count", 0),
            "unbound_work_lane_count": coordination.get("unbound_work_lane_count", 0),
        },
        diagnostics=(validation,),
        required_gaps=tuple(status_payload.get("required_gaps", ())) + validation_gaps,
        next_actions=tuple(orientation_actions),
        data=status_payload,
    )
    if json_output:
        emit(result, json_output, enforce=False)
        return
    for line in _orient.human_orientation_lines(orientation):
        print(line)


@app.command
def orient(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Orient a human or agent without minting repository truth."""
    repo = resolve_root(root)
    status_payload = workspace_status(repo)
    report_payload = scorecard_report(repo)
    packet = _orient.orientation_packet(
        status_payload=status_payload,
        report_payload=report_payload,
    )
    where = cast("dict[str, Any]", packet["where"])
    capability = cast("dict[str, Any]", packet["capability"])
    coordination = cast("dict[str, Any]", packet["coordination"])
    readiness = cast("dict[str, Any]", packet["readiness"])
    packet_actions = cast("list[str]", packet["next_actions"])
    result = EthosResult(
        command="orient",
        ok=True,
        state="oriented",
        summary={
            "role": where["role"],
            "capability": capability["current_actor_capability"],
            "foreign_work_lane_count": coordination["foreign_work_lane_count"],
            "unbound_work_lane_count": coordination["unbound_work_lane_count"],
            "governance_gap_count": readiness["governance_gap_count"],
            "parity_pending_count": readiness["parity_pending_count"],
        },
        next_actions=tuple(packet_actions),
        data={"orientation": packet},
    )
    if json_output:
        emit(result, json_output, enforce=False)
        return
    for line in _orient.human_orientation_lines(packet):
        print(line)


@app.command
def plan(
    *,
    changed: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Plan deterministic action graph."""
    repo = resolve_root(root)
    status_payload = workspace_status(repo)
    paths = tuple(status_payload["changed_paths"]) if changed else ()
    graph = _plan.graph_for_paths(paths)
    matched_rules, required_gates = _plan.matching_rule_gates(repo, paths)
    result = EthosResult(
        command="plan",
        ok=True,
        state="planned",
        summary={
            "changed": changed,
            "action_count": len(graph.nodes),
            "matched_rule_count": len(matched_rules),
            "required_gate_count": len(required_gates),
        },
        next_actions=("ethos prove --json",),
        data={
            "changed_paths": list(paths),
            "matched_rules": matched_rules,
            "required_gates": required_gates,
            "action_graph": graph.to_dict(),
        },
    )
    emit(result, json_output, enforce=False)


@app.command
def prove(
    *,
    objective: str = "ethos proof",
    execute: bool = False,
    gate: tuple[str, ...] = (),
    full: bool = False,
    expect_head: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Produce a local proof-readiness summary."""
    repo = resolve_root(root)
    current_head = _gitio.current_head(repo)
    audit = _status.audit_for_root(
        repo, openspec_mode="deep" if full else "shape", current_head=current_head
    )
    graph = gate_graph(gate, full=full)
    gates_by_id = gate_registry()
    runner = (
        LocalSubprocessRunner(inprocess_handler=_run_inprocess_cli_gate)
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
    ok = (
        bool(audit["ok"])
        and runs_ok
        and graph.validate().ok
        and not failed_gate_gaps
        and not proof_gaps
        and not trust_gaps
        and not head_gaps
    )
    result_state = "proven" if ok and execute else "ready" if ok else "gapped"
    if result_state == "proven":
        # Persist a HEAD-keyed, self-authenticating proof record so land/publish can
        # require executed proof at this exact HEAD. The full evidence body is stored
        # so the record's digest is later recomputable — a forged record fails.
        record_executed_proof(repo, evidence.to_dict())
    next_actions = (
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
            + tuple(graph.validate().gaps)
            + failed_gate_gaps
            + proof_gaps
            + trust_gaps
            + head_gaps
        ),
        next_actions=next_actions,
        data={
            "repository_audit": audit,
            "executed": execute,
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
    emit(result, json_output, enforce=False)


@app.command
def land(
    *,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    closeout: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report land readiness."""
    repo = resolve_root(root)
    if closeout:
        decision = evaluate_closeout_mutation(
            MutationRequest(
                command="closeout",
                apply=apply,
                authorized=authorize,
                expect_head=expect_head,
            ),
            root=repo,
            current_head=_gitio.current_head(repo),
        )
        audit_root = _land.closeout_audit_root(repo, decision)
        audit = _land.repository_audit_after_admission(audit_root, decision)
        openspec_lifecycle = openspec_completed_active_changes_report(audit_root)
        openspec_gaps = tuple(str(gap) for gap in openspec_lifecycle["required_gaps"])
        gaps = tuple(audit["required_gaps"]) + decision.gaps + openspec_gaps
        closeout_bootstrap = _land.closeout_bootstrap_package(
            repo=repo,
            audit_root=audit_root,
            required_gaps=gaps,
        )
        ok = bool(audit["ok"]) and decision.ok and bool(openspec_lifecycle["ok"])
        accepted_update: dict[str, object] = {}
        if ok and apply:
            accepted_update = apply_candidate_to_accepted(
                root=repo,
                authorized=authorize,
                expect_head=expect_head,
            )
            gaps = gaps + tuple(accepted_update["required_gaps"])
            ok = bool(accepted_update["ok"])
        if ok and not apply:
            land_state = "ready_to_closeout"
        elif gaps:
            land_state = "blocked"
        else:
            land_state = str(accepted_update.get("state") or decision.state)
        result = EthosResult(
            command="land",
            ok=ok,
            state=land_state,
            required_gaps=gaps,
            next_actions=_land.closeout_next_actions(
                ok=ok, gaps=gaps, current_head=_gitio.current_head(repo)
            ),
            data={
                "repository_audit": audit,
                "openspec_lifecycle": openspec_lifecycle,
                "accepted_update": accepted_update,
                "closeout_bootstrap": closeout_bootstrap,
                "mutation": {
                    "apply": apply,
                    "authorized": authorize,
                    "expect_head": expect_head,
                    "current_head": _gitio.current_head(repo),
                    "decision": decision.state,
                    "closeout": True,
                },
            },
        )
        emit(result, json_output, enforce=apply)
        return
    status_payload = workspace_status(repo)
    closeout_support = dict(status_payload.get("closeout_support", {}))
    closeout_gaps: tuple[str, ...] = ()
    if status_payload.get("role") == "work_lane" and not closeout_support.get("supported"):
        closeout_gaps = tuple(str(gap) for gap in closeout_support.get("required_gaps", ()))
    decision = evaluate_mutation(
        MutationRequest(
            command="land",
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
        ),
        root=repo,
        current_head=_gitio.current_head(repo),
    )
    audit = _land.repository_audit_after_admission(repo, decision)
    openspec_lifecycle = openspec_completed_active_changes_report(repo)
    openspec_gaps = tuple(str(gap) for gap in openspec_lifecycle["required_gaps"])
    gaps = tuple(audit["required_gaps"]) + decision.gaps + closeout_gaps + openspec_gaps
    ok = bool(audit["ok"]) and decision.ok and bool(openspec_lifecycle["ok"])
    if closeout_gaps:
        ok = False
    candidate_update: dict[str, object] = {}
    if ok and apply:
        candidate_update = apply_land_to_candidate(
            root=repo,
            authorized=authorize,
            expect_head=expect_head,
            admitted_decision=decision,
        )
        gaps = gaps + tuple(candidate_update["required_gaps"])
        ok = bool(candidate_update["ok"])
    elif ok:
        candidate_update = candidate_base_report(root=repo)
        if not candidate_update["ok"]:
            gaps = gaps + tuple(candidate_update["required_gaps"])
            ok = False
    if ok and not apply:
        land_state = "ready_to_land"
    elif gaps:
        land_state = "blocked"
    else:
        land_state = str(candidate_update.get("state") or decision.state)
    result = EthosResult(
        command="land",
        ok=ok,
        state=land_state,
        required_gaps=gaps,
        next_actions=_land.land_next_actions(
            ok=ok, gaps=gaps, current_head=_gitio.current_head(repo)
        ),
        data={
            "repository_audit": audit,
            "openspec_lifecycle": openspec_lifecycle,
            "candidate_update": candidate_update,
            "closeout_support": closeout_support,
            "mutation": {
                "apply": apply,
                "authorized": authorize,
                "expect_head": expect_head,
                "current_head": _gitio.current_head(repo),
                "decision": decision.state,
            },
        },
    )
    emit(result, json_output, enforce=apply)


@app.command
def publish(
    *,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report publish readiness without pushing."""
    repo = resolve_root(root)
    decision = evaluate_mutation(
        MutationRequest(
            command="publish",
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
        ),
        root=repo,
        current_head=_gitio.current_head(repo),
    )
    audit = _land.repository_audit_after_admission(repo, decision)
    gaps = tuple(audit["required_gaps"]) + decision.gaps
    ok = bool(audit["ok"]) and decision.ok
    branch = workspace_status(repo)["branch"]
    result = EthosResult(
        command="publish",
        ok=ok,
        state=("ready_to_publish" if ok and not apply else decision.state),
        required_gaps=gaps,
        next_actions=("ethos report",) if ok else ("ethos land --json",),
        data={
            "repository_audit": audit,
            "remote_push": "not_performed",
            "publication": _land.publication_readiness(
                branch=str(branch),
                local_ok=ok,
                policy=load_branch_role_policy(repo),
            ),
            "mutation": {
                "apply": apply,
                "authorized": authorize,
                "expect_head": expect_head,
                "current_head": _gitio.current_head(repo),
                "decision": decision.state,
            },
        },
    )
    emit(result, json_output, enforce=apply)


@app.command(show=False)
def doctor(
    *,
    root: RootOption | None = None,
    init_state: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Inspect local host readiness."""
    repo = resolve_root(root)
    db_path = repo / ".ethos" / "state" / "state.sqlite"
    if init_state:
        initialize_state(db_path)
    result = EthosResult(
        command="doctor",
        ok=True,
        state="ready",
        summary={"state_db_exists": db_path.exists()},
        next_actions=("ethos status",),
        data={"state_db": str(db_path), "initialized": init_state},
    )
    emit(result, json_output, enforce=False)


@app.command
def init(
    *,
    root: RootOption | None = None,
    dry_run: bool = True,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    profile: str | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Initialize ETHOS adoption for a repository."""
    target = resolve_root(root)
    current_head = _gitio.current_head(target)
    mutation_gaps = _status.adoption_mutation_gaps(
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        current_head=current_head,
    )
    do_apply = apply and not mutation_gaps
    plan_payload = adoption_plan(target, profile=profile, apply=do_apply)
    required_gaps = tuple(mutation_gaps) + tuple(plan_payload.get("required_gaps", ()))
    ok = not required_gaps
    hooks_armed = False
    if do_apply and ok:
        # Arm write-admission by construction: wire core.hooksPath so the pre-commit
        # gate is active without a manual `ethos hook install` (tao FP#2 — the gate
        # must not depend on being remembered).
        hooks_armed = _gitio.set_hooks_path(target, ".githooks")
    result = EthosResult(
        command="init",
        ok=ok,
        state="applied" if do_apply and ok else "blocked" if required_gaps else "planned",
        summary={
            "planned_file_count": len(plan_payload["planned_files"]),
            "hooks_armed": hooks_armed,
        },
        next_actions=("ethos status",),
        required_gaps=required_gaps,
        data=plan_payload,
    )
    result.data["mutation"] = {
        "apply": apply,
        "authorized": authorize,
        "expect_head": expect_head,
        "current_head": current_head,
    }
    emit(result, json_output, enforce=apply)


@app.command
def adopt(
    *,
    root: RootOption | None = None,
    dry_run: bool = True,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    profile: str | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Plan or apply ETHOS adoption for a repository."""
    target = resolve_root(root)
    current_head = _gitio.current_head(target)
    mutation_gaps = _status.adoption_mutation_gaps(
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        current_head=current_head,
    )
    do_apply = apply and not mutation_gaps
    plan_payload = adoption_plan(target, profile=profile, apply=do_apply)
    required_gaps = tuple(mutation_gaps) + tuple(plan_payload.get("required_gaps", ()))
    ok = not required_gaps
    hooks_armed = False
    if do_apply and ok:
        # Arm write-admission by construction (tao FP#2 — not dependent on a manual step).
        hooks_armed = _gitio.set_hooks_path(target, ".githooks")
    result = EthosResult(
        command="adopt",
        ok=ok,
        state="applied" if do_apply and ok else "blocked" if required_gaps else "planned",
        summary={
            "planned_file_count": len(plan_payload["planned_files"]),
            "hooks_armed": hooks_armed,
        },
        next_actions=("ethos status",),
        required_gaps=required_gaps,
        data=plan_payload,
    )
    result.data["mutation"] = {
        "apply": apply,
        "authorized": authorize,
        "expect_head": expect_head,
        "current_head": current_head,
    }
    emit(result, json_output, enforce=apply)


@app.command
def report(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit a concise scorecard."""
    payload = scorecard_report(resolve_root(root))
    result = EthosResult(
        command="report",
        ok=bool(payload["ok"]),
        state="ready" if payload["ok"] else "gapped",
        summary=payload["summary"],
        required_gaps=tuple(payload["required_gaps"]),
        next_actions=tuple(payload["next_actions"]),
        data=payload["data"],
    )
    emit(result, json_output, enforce=False)


@app.command(show=False)
def explain(gap: str, *, json_output: JsonFlag = False) -> None:
    """Explain a required gap as a read-only invalid-state projection."""
    data = explain_gap(gap)
    category_id = str(data["invalid_state"]["id"])
    result = EthosResult(
        command="explain",
        ok=category_id != UNCLASSIFIED,
        state="explained" if category_id != UNCLASSIFIED else "unclassified",
        summary={"gap": gap, "invalid_state": category_id},
        required_gaps=() if category_id != UNCLASSIFIED else (f"unclassified_invalid_state:{gap}",),
        data=data,
    )
    emit(result, json_output, enforce=False)


@app.command(show=False)
def docs(
    topic: str = "index",
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Locate documentation for a topic."""
    repo = resolve_root(root)
    normalized = topic.removeprefix("ethos:").removeprefix("docs:")
    matches = [
        entry
        for entry in build_docs_registry(repo)
        if normalized
        in {
            Path(entry["path"]).stem,
            entry["subject"],
            entry["subject"].split(":", 1)[-1],
        }
    ]
    path = matches[0]["path"] if matches else ""
    result = EthosResult(
        command="docs",
        ok=bool(path),
        state="located" if path else "missing",
        summary={"topic": topic},
        required_gaps=() if path else (f"docs_topic_missing:{topic}",),
        data={"path": path, "matches": matches},
    )
    emit(result, json_output, enforce=False)


@app.command(show=False)
def audit(
    *,
    mode: str = "deep",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Audit repository governance against the active profile."""
    repo = resolve_root(root)
    if mode not in {"shape", "deep"}:
        result = EthosResult(
            command="audit",
            ok=False,
            state="invalid",
            required_gaps=(f"invalid_audit_mode:{mode}",),
            next_actions=("ethos audit --mode shape", "ethos audit --mode deep"),
            data={"mode": mode, "allowed_modes": ["shape", "deep"]},
        )
        emit(result, json_output, enforce=False)
        return
    audit_payload = _status.audit_for_root(repo, openspec_mode=mode)
    result = EthosResult(
        command="audit",
        ok=bool(audit_payload["ok"]),
        state="clean" if audit_payload["ok"] else "gapped",
        summary={"openspec_mode": mode},
        required_gaps=tuple(audit_payload["required_gaps"]),
        next_actions=("ethos report",) if audit_payload["ok"] else ("ethos audit --mode deep",),
        data=audit_payload,
    )
    emit(result, json_output, enforce=False)


@app.command(show=False)
def openspec(
    *,
    change: str | None = None,
    lifecycle: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Audit official OpenSpec governance state."""
    repo = resolve_root(root)
    report = openspec_governance_report(repo, change=change, lifecycle=lifecycle)
    result = EthosResult(
        command="openspec",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "gapped",
        summary={
            "change": report["change"],
            "schema_name": report["schema_name"],
            "lifecycle": lifecycle,
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos audit",),
        data=report,
    )
    emit(result, json_output, enforce=False)


def main() -> None:
    import sys

    _load_command_groups(sys.argv[1:])
    app()


if __name__ == "__main__":
    main()
