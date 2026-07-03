from __future__ import annotations

import hashlib
import os
import tomllib
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated

from cyclopts import Parameter

import ethos_assistants.playbooks as playbooks_module
import ethos_repository.repository_audit as repository_audit_module
from ethos.adapters import git as _gitio
from ethos.adapters import quality_tool as _qtool
from ethos.domain import land as _land
from ethos.domain import plan as _plan
from ethos.domain import prove as _prove
from ethos.domain import status as _status
from ethos_adapters.commit_policy import signature_policy_report
from ethos_adapters.context_index import context_eval_report
from ethos_adapters.context_index import purge_context_index
from ethos_adapters.context_index import rebuild_context_index
from ethos_adapters.context_index import search_context_index
from ethos_adapters.hook_admission import hook_admission_report
from ethos_adapters.lanes import bind_work_lane_claim
from ethos_adapters.lanes import bootstrap_candidate
from ethos_adapters.lanes import refresh_work_lane_base
from ethos_adapters.lanes import retire_landed_work_lanes
from ethos_adapters.lanes import start_work_lane
from ethos_adapters.mutation import MutationDecision
from ethos_adapters.mutation import MutationRequest
from ethos_adapters.mutation import apply_candidate_to_accepted
from ethos_adapters.mutation import apply_land_to_candidate
from ethos_adapters.mutation import candidate_base_report
from ethos_adapters.mutation import evaluate_closeout_mutation
from ethos_adapters.mutation import evaluate_mutation
from ethos_adapters.openspec_native import (
    completed_active_changes_report as openspec_completed_active_changes_report,
)
from ethos_adapters.openspec_native import openspec_governance_report
from ethos_adapters.prewrite import prewrite_guard
from ethos_adapters.runner import ActionRunResult
from ethos_adapters.runner import DryRunRunner
from ethos_adapters.runner import LocalSubprocessRunner
from ethos_adapters.runner import classify_action_result
from ethos_adapters.state import initialize_state
from ethos_adapters.status import workspace_status
from ethos_assistants.context import context_bundle
from ethos_assistants.mcp import mcp_manifest
from ethos_assistants.playbooks import playbooks_report
from ethos_assistants.playbooks import route_playbook
from ethos_assistants.projections import projection_contract
from ethos_assistants.server import mcp_server_descriptor
from ethos_contracts.branch_roles import BranchRolePolicy
from ethos_contracts.branch_roles import load_branch_role_policy
from ethos_contracts.context_projection import context_projection_contract
from ethos_contracts.context_projection import context_retrieval_smoke_queries
from ethos_contracts.package_ontology import package_ontology_report
from ethos_contracts.package_ontology import workspace_package_config_report
from ethos_contracts.rules import RuleAttestation
from ethos_contracts.rules import RuleFactSnapshot
from ethos_core.result import EthosResult
from ethos_quality.docs_profile import docs_quality_profile
from ethos_quality.profiles import product_quality_profile
from ethos_quality.profiles import tool_profiles
from ethos_quality.proof_policy import proof_lattice
from ethos_repository.attestation import release_attestation
from ethos_repository.attestation import sbom_projection
from ethos_repository.claims import claims_report
from ethos_repository.command_registry import command_registry_report
from ethos_repository.coupling import coupling_audit_report
from ethos_repository.docs_registry import build_docs_registry
from ethos_repository.docs_registry import command_examples_report
from ethos_repository.docs_registry import docs_health_report
from ethos_repository.docs_registry import docs_quality_report
from ethos_repository.evidence import EvidenceSet
from ethos_repository.evidence import ProofRun
from ethos_repository.evidence import provenance_envelope
from ethos_repository.evidence import trim_output
from ethos_repository.evolution import campaign_report
from ethos_repository.evolution import evolution_ledger
from ethos_repository.evolution import evolution_report
from ethos_repository.gates import gate_graph
from ethos_repository.gates import gate_registry
from ethos_repository.parity import build_tracked_parity_evidence
from ethos_repository.parity import parity_gaps_report
from ethos_repository.parity import parity_ledger_report
from ethos_repository.parity import shadow_parity_report
from ethos_repository.parity import write_tracked_parity_evidence
from ethos_repository.planner import adoption_plan
from ethos_repository.planner import adoption_scaffold_report
from ethos_repository.planner import available_profiles
from ethos_repository.release import release_policy_report
from ethos_repository.rules import compile_rules
from ethos_repository.rules import coverage_report
from ethos_repository.rules import explain_rules_target
from ethos_repository.rules import policy_exceptions_report
from ethos_repository.rules import rules_check_report
from ethos_repository.rules import rules_evaluation_report
from ethos_repository.schema_validation import schema_validation_report
from ethos_repository.standards import standard_adapter_registry

if TYPE_CHECKING:
    from ethos_core.action_graph import ActionGraph
    from ethos_core.action_graph import ActionNode

# Command-group modules register their commands onto the shared *_app objects at
# import time; importing them here wires those groups into the CLI. Each group
# imports only its own domain deps, so a group's heavy dependencies load only when
# that group is imported (lazy path for the common commands).
from ethos.surface.cli import fleet as _fleet_group  # noqa: F401
from ethos.surface.cli import intake as _intake_group  # noqa: F401
from ethos.surface.cli._base import ASSISTANT_TRUTH_BOUNDARY
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import app
from ethos.surface.cli._base import assistants_app
from ethos.surface.cli._base import campaign_app
from ethos.surface.cli._base import emit as _emit
from ethos.surface.cli._base import hook_app
from ethos.surface.cli._base import lane_app
from ethos.surface.cli._base import parity_app
from ethos.surface.cli._base import playbooks_app
from ethos.surface.cli._base import quality_app
from ethos.surface.cli._base import resolve_root as _root
from ethos.surface.cli._base import rules_app


def _current_head(root: Path) -> str:
    return _gitio.current_head(root)


def _current_tracked_head(root: Path) -> str:
    return _gitio.current_tracked_head(root)


def _acceptable_parity_product_heads(root: Path, adopter: str | None) -> tuple[str, ...]:
    return _land.acceptable_parity_product_heads(root, adopter)


def _acceptable_parity_target_heads(
    root: Path,
    target: Path | None,
    adopter: str | None,
) -> tuple[str, ...]:
    return _land.acceptable_parity_target_heads(root, target, adopter)


def _adoption_mutation_gaps(
    *,
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    current_head: str,
) -> tuple[str, ...]:
    return _status.adoption_mutation_gaps(
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        current_head=current_head,
    )


def _graph_for_paths(paths: tuple[str, ...]) -> ActionGraph:
    return _plan.graph_for_paths(paths)


def _audit_for_root(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
    return _status.audit_for_root(root, openspec_mode=openspec_mode)


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
        root=root, gate_id=gate_id, tool=tool, command=command, files=files,
    )


def _code_size_report(root: Path) -> dict[str, object]:
    return _prove.code_size_report(root)


def _matching_rule_gates(
    root: Path,
    paths: tuple[str, ...],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    return _plan.matching_rule_gates(root, paths)


def _workspace_status_validation(repo: Path, payload: dict[str, object]) -> dict[str, object]:
    return _prove.workspace_status_validation(repo, payload)


def _workspace_status_validation_gaps(validation: dict[str, object]) -> tuple[str, ...]:
    return _prove.workspace_status_validation_gaps(validation)


def _command_data_validation(
    repo: Path,
    *,
    schema_name: str,
    payload: dict[str, object],
) -> dict[str, object]:
    return _prove.command_data_validation(repo, schema_name=schema_name, payload=payload)


def _publication_readiness(
    *,
    branch: str,
    local_ok: bool,
    policy: BranchRolePolicy,
) -> dict[str, object]:
    return _land.publication_readiness(branch=branch, local_ok=local_ok, policy=policy)


def _campaign_closeout_report(
    *,
    repo: Path,
    adopter: str,
    target: Path,
) -> dict[str, object]:
    return _land.campaign_closeout_report(repo=repo, adopter=adopter, target=target)


@app.command
def status(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Inspect repository state."""
    repo = _root(root)
    status_payload = workspace_status(repo)
    validation = _workspace_status_validation(repo, status_payload)
    validation_gaps = _workspace_status_validation_gaps(validation)
    ok = bool(validation["ok"])
    result = EthosResult(
        command="status",
        ok=ok,
        state="invalid" if not ok else "dirty" if status_payload["dirty"] else "ready",
        summary={
            "root": str(repo),
            "branch": status_payload["branch"],
            "changed_path_count": len(status_payload["changed_paths"]),
        },
        diagnostics=(validation,),
        required_gaps=tuple(status_payload.get("required_gaps", ())) + validation_gaps,
        next_actions=("ethos plan --changed",),
        data=status_payload,
    )
    _emit(result, json_output)


@lane_app.command(name="status")
def lane_status(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Inspect Work Lane topology and foreign lanes."""
    repo = _root(root)
    status_payload = workspace_status(repo)
    validation = _workspace_status_validation(repo, status_payload)
    validation_gaps = _workspace_status_validation_gaps(validation)
    ok = bool(validation["ok"])
    result = EthosResult(
        command="lane status",
        ok=ok,
        state="ready" if ok else "invalid",
        summary={
            "branch": status_payload["branch"],
            "role": status_payload["role"],
            "foreign_work_lane_count": len(status_payload["foreign_work_lanes"]),
        },
        diagnostics=(validation,),
        required_gaps=tuple(status_payload.get("required_gaps", ())) + validation_gaps,
        next_actions=("ethos lane prewrite <path>",),
        data=status_payload,
    )
    _emit(result, json_output)


@lane_app.command
def candidate(
    *,
    apply: bool = False,
    path: Annotated[Path | None, Parameter(name="--path")] = None,
    expect_head: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Bootstrap or inspect the local candidate train."""
    repo = _root(root)
    report = bootstrap_candidate(root=repo, path=path, expect_head=expect_head, apply=apply)
    result = EthosResult(
        command="lane candidate",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "head": report["head"],
            "path": report["path"],
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos lane start <name>",) if report["ok"] else ("ethos status",),
        data=report,
    )
    _emit(result, json_output)


@lane_app.command
def prewrite(
    paths: tuple[Path, ...],
    *,
    editor_root: Annotated[Path | None, Parameter(name="--editor-root")] = None,
    require_editor_root: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check tracked write admission before editing files."""
    repo = _root(root)
    report = prewrite_guard(
        root=repo,
        paths=[path if path.is_absolute() else repo / path for path in paths],
        editor_root=editor_root,
        require_editor_root=require_editor_root,
    )
    result = EthosResult(
        command="lane prewrite",
        ok=bool(report["ok"]),
        state="admitted" if report["ok"] else "blocked",
        summary={
            "path_count": len(paths),
            "role": report["role"],
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos lane start <name>",) if not report["ok"] else (),
        data=report,
    )
    _emit(result, json_output, enforce=True)


@hook_app.command
def admit(
    layer: str,
    paths: tuple[Path, ...] = (),
    *,
    command: Annotated[str, Parameter(name="--command")] = "",
    editor_root: Annotated[Path | None, Parameter(name="--editor-root")] = None,
    expected_root: Annotated[Path | None, Parameter(name="--expected-root")] = None,
    require_editor_root: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Evaluate hook-time write admission before a host mutates tracked files."""
    repo = _root(root)
    report = hook_admission_report(
        root=repo,
        layer=layer,
        paths=[path if path.is_absolute() else repo / path for path in paths],
        editor_root=editor_root,
        expected_root=expected_root,
        require_editor_root=require_editor_root,
        command=command,
    )
    decision = report.get("decision", {})
    decision_action = ""
    if isinstance(decision, dict):
        decision_action = str(decision.get("action", ""))
    result = EthosResult(
        command="hook admit",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "layer": report["layer"],
            "role": report["role"],
            "decision": decision_action,
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos lane prewrite <path>",) if not report["ok"] else (),
        data=report,
    )
    _emit(result, json_output, enforce=True)


@hook_app.command
def install(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Install the write-admission git hooks by wiring core.hooksPath to .githooks."""
    repo = _root(root)
    hook_path = repo / ".githooks" / "pre-commit"
    gaps: list[str] = []
    if not hook_path.exists():
        gaps.append("hook_script_missing:.githooks/pre-commit")
    wired = _gitio.set_hooks_path(repo, ".githooks") if not gaps else False
    if not gaps and not wired:
        gaps.append("hooks_path_wire_failed")
    result = EthosResult(
        command="hook install",
        ok=not gaps,
        state="installed" if not gaps else "blocked",
        summary={"hooks_path": ".githooks", "wired": wired},
        required_gaps=tuple(gaps),
        next_actions=(
            ("git commit — the pre-commit admission gate is now active",) if not gaps else ()
        ),
        data={
            "hooks_path": ".githooks",
            "hook_script": ".githooks/pre-commit",
            "wired": wired,
        },
    )
    _emit(result, json_output, enforce=True)


@lane_app.command
def start(
    name: str,
    *,
    path: Annotated[Path, Parameter(name="--path")],
    owner: str,
    claim_id: Annotated[str | None, Parameter(name="--claim-id")] = None,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Start an owned Work Lane and acquire a local lease."""
    repo = _root(root)
    report = start_work_lane(
        root=repo,
        name=name,
        path=path,
        owner=owner,
        claim_id=claim_id,
        apply=apply,
    )
    result = EthosResult(
        command="lane start",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "path": report.get("path", ""),
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos lane prewrite <path>",) if report["ok"] else (),
        data=report,
    )
    _emit(result, json_output)


@lane_app.command(name="refresh-base")
def lane_refresh_base(
    *,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Replay the current Work Lane onto the configured candidate branch."""
    repo = _root(root)
    report = refresh_work_lane_base(
        root=repo,
        apply=apply,
        authorized=authorize,
        expect_head=expect_head,
    )
    result = EthosResult(
        command="lane refresh-base",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "candidate_branch": report["candidate_branch"],
            "head": report["head"],
            "candidate_head": report["candidate_head"],
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos land --json",) if report["ok"] else ("ethos status --json",),
        data=report,
    )
    _emit(result, json_output)


@lane_app.command(name="bind-claim")
def lane_bind_claim(
    *,
    claim_id: Annotated[str, Parameter(name="--claim-id")],
    branch: Annotated[str | None, Parameter(name="--branch")] = None,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Bind an existing Work Lane lease to a trust-bearing claim."""
    repo = _root(root)
    report = bind_work_lane_claim(
        root=repo,
        branch=branch,
        claim_id=claim_id,
        apply=apply,
    )
    result = EthosResult(
        command="lane bind-claim",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "claim_id": report["claim_id"],
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos lane status",) if report["ok"] else ("ethos lane start <name>",),
        data=report,
    )
    _emit(result, json_output)


@app.command
def plan(
    *,
    changed: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Plan deterministic action graph."""
    repo = _root(root)
    status_payload = workspace_status(repo)
    paths = tuple(status_payload["changed_paths"]) if changed else ()
    graph = _graph_for_paths(paths)
    matched_rules, required_gates = _matching_rule_gates(repo, paths)
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
    _emit(result, json_output)


@lane_app.command(name="retire-landed")
def lane_retire_landed(
    *,
    branch: str | None = None,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Retire a landed Work Lane after it is merged into the accepted root."""
    repo = _root(root)
    report = retire_landed_work_lanes(root=repo, branch=branch, apply=apply)
    result = EthosResult(
        command="lane retire-landed",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "landed_lane_count": sum(1 for lane in report["lanes"] if lane["retire_ready"]),
            "selected_branch": branch or "",
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos status",) if report["ok"] else ("ethos lane status",),
        data=report,
    )
    _emit(result, json_output)


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
    repo = _root(root)
    current_head = _current_head(repo)
    audit = _audit_for_root(repo, openspec_mode="deep" if full else "shape")
    graph = gate_graph(gate, full=full)
    gates_by_id = gate_registry()
    runner = (
        LocalSubprocessRunner(inprocess_handler=_run_inprocess_cli_gate)
        if execute
        else DryRunRunner()
    )
    proof_runs = tuple(
        ProofRun.from_adapter_result(
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
    proof_gaps: tuple[str, ...] = ("full_proof_requires_execute",) if full and not execute else ()
    trust_gaps: tuple[str, ...] = (
        ("trust_bearing_proof_missing",)
        if execute and verdicts_ok and not trust_bearing_ok
        else ()
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
        and not proof_gaps
        and not head_gaps
    )
    result_state = "proven" if ok and execute else "ready" if ok else "gapped"
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
    _emit(result, json_output)


def _run_inprocess_cli_gate(node: ActionNode, root: Path) -> ActionRunResult | None:
    if not (len(node.command) >= 4 and node.command[1:3] == ("-m", "ethos.cli")):
        return None
    if "--json" not in node.command:
        return None
    stdout = StringIO()
    stderr = StringIO()
    previous_cwd = Path.cwd()
    exit_code = 0
    try:
        os.chdir(root)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                app(list(node.command[3:]), exit_on_error=False)
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1
    except BaseException as exc:  # pragma: no cover - returned as runner failure.
        exit_code = 1
        stderr.write(f"{type(exc).__name__}: {exc}")
    finally:
        os.chdir(previous_cwd)
    state, diagnostics = classify_action_result(
        exit_code=exit_code,
        stdout=stdout.getvalue(),
    )
    return ActionRunResult(
        action_id=node.id,
        command=node.command,
        state=state,
        exit_code=exit_code,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
        diagnostics=diagnostics,
    )


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
    repo = _root(root)
    if closeout:
        decision = evaluate_closeout_mutation(
            MutationRequest(
                command="closeout",
                apply=apply,
                authorized=authorize,
                expect_head=expect_head,
            ),
            root=repo,
            current_head=_current_head(repo),
        )
        audit_root = _closeout_audit_root(repo, decision)
        audit = _repository_audit_after_admission(audit_root, decision)
        openspec_lifecycle = openspec_completed_active_changes_report(audit_root)
        openspec_gaps = tuple(str(gap) for gap in openspec_lifecycle["required_gaps"])
        gaps = tuple(audit["required_gaps"]) + decision.gaps + openspec_gaps
        closeout_bootstrap = _closeout_bootstrap_package(
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
            next_actions=(
                ("ethos lane retire-landed --branch <work-branch>",)
                if ok
                else ("ethos prove --json",)
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
                    "current_head": _current_head(repo),
                    "decision": decision.state,
                    "closeout": True,
                },
            },
        )
        _emit(result, json_output)
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
        current_head=_current_head(repo),
    )
    audit = _repository_audit_after_admission(repo, decision)
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
        next_actions=_land_next_actions(ok=ok, gaps=gaps, current_head=_current_head(repo)),
        data={
            "repository_audit": audit,
            "openspec_lifecycle": openspec_lifecycle,
            "candidate_update": candidate_update,
            "closeout_support": closeout_support,
            "mutation": {
                "apply": apply,
                "authorized": authorize,
                "expect_head": expect_head,
                "current_head": _current_head(repo),
                "decision": decision.state,
            },
        },
    )
    _emit(result, json_output)


def _land_next_actions(
    *,
    ok: bool,
    gaps: tuple[str, ...],
    current_head: str,
) -> tuple[str, ...]:
    return _land.land_next_actions(ok=ok, gaps=gaps, current_head=current_head)


def _closeout_audit_root(repo: Path, decision: MutationDecision) -> Path:
    return _land.closeout_audit_root(repo, decision)


def _closeout_bootstrap_package(
    *,
    repo: Path,
    audit_root: Path,
    required_gaps: tuple[str, ...],
) -> dict[str, object]:
    return _land.closeout_bootstrap_package(
        repo=repo, audit_root=audit_root, required_gaps=required_gaps,
    )


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
    repo = _root(root)
    decision = evaluate_mutation(
        MutationRequest(
            command="publish",
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
        ),
        root=repo,
        current_head=_current_head(repo),
    )
    audit = _repository_audit_after_admission(repo, decision)
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
            "publication": _publication_readiness(
                branch=str(branch),
                local_ok=ok,
                policy=load_branch_role_policy(repo),
            ),
            "mutation": {
                "apply": apply,
                "authorized": authorize,
                "expect_head": expect_head,
                "current_head": _current_head(repo),
                "decision": decision.state,
            },
        },
    )
    _emit(result, json_output)


@app.command(show=False)
def doctor(
    *,
    root: RootOption | None = None,
    init_state: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Inspect local host readiness."""
    repo = _root(root)
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
    _emit(result, json_output)


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
    target = _root(root)
    current_head = _current_head(target)
    mutation_gaps = _adoption_mutation_gaps(
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        current_head=current_head,
    )
    do_apply = apply and not mutation_gaps
    plan_payload = adoption_plan(target, profile=profile, apply=do_apply)
    required_gaps = tuple(mutation_gaps) + tuple(plan_payload.get("required_gaps", ()))
    ok = not required_gaps
    result = EthosResult(
        command="init",
        ok=ok,
        state="applied" if do_apply and ok else "blocked" if required_gaps else "planned",
        summary={"planned_file_count": len(plan_payload["planned_files"])},
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
    _emit(result, json_output)


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
    target = _root(root)
    current_head = _current_head(target)
    mutation_gaps = _adoption_mutation_gaps(
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        current_head=current_head,
    )
    do_apply = apply and not mutation_gaps
    plan_payload = adoption_plan(target, profile=profile, apply=do_apply)
    required_gaps = tuple(mutation_gaps) + tuple(plan_payload.get("required_gaps", ()))
    ok = not required_gaps
    result = EthosResult(
        command="adopt",
        ok=ok,
        state="applied" if do_apply and ok else "blocked" if required_gaps else "planned",
        summary={"planned_file_count": len(plan_payload["planned_files"])},
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
    _emit(result, json_output)


@quality_app.command
def asset_policy(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report repository asset quality policy."""
    profile = product_quality_profile()
    result = EthosResult(
        command="quality asset-policy",
        ok=True,
        state="clean",
        summary={"asset_class_count": len(profile["asset_classes"])},
        data=profile,
    )
    _emit(result, json_output)


@quality_app.command(name="docs")
def quality_docs(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report documentation quality profile and registry health."""
    repo = _root(root)
    profile = docs_quality_profile()
    report = docs_quality_report(repo)
    result = EthosResult(
        command="quality docs",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data={
            "profile": profile,
            "style_goals": profile["style_goals"],
            "health": report,
        },
    )
    _emit(result, json_output)


@quality_app.command
def proof_policy(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report proof-state lattice and trust-bearing rules."""
    lattice = proof_lattice()
    result = EthosResult(
        command="quality proof-policy",
        ok=True,
        state="clean",
        summary={"state_count": len(lattice["states"])},
        data=lattice,
    )
    _emit(result, json_output)


@quality_app.command(name="tool-profiles")
def tool_profiles_command(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report quality tool adapter profiles."""
    profiles = tool_profiles()
    result = EthosResult(
        command="quality tool-profiles",
        ok=True,
        state="clean",
        summary={"tool_adapter_count": len(profiles["tool_adapters"])},
        data=profiles,
    )
    _emit(result, json_output)


@quality_app.command(name="markdown-links")
def markdown_links(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run markdown link checks through the configured adapter."""
    repo = _root(root)
    files = [
        path
        for path in _git_files(repo, "*.md")
        if not path.startswith(("docs/evidence/", "docs/archive/"))
    ]
    report = _quality_tool_report(
        root=repo,
        gate_id="markdown-links",
        tool="lychee",
        command=["lychee", "--offline", "--no-progress", *files],
        files=files,
    )
    result = EthosResult(
        command="quality markdown-links",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command(name="shell")
def shell_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run shell script lint checks through ShellCheck."""
    repo = _root(root)
    files = _git_files(repo, "*.sh")
    report = _quality_tool_report(
        root=repo,
        gate_id="shell-lint",
        tool="shellcheck",
        command=["shellcheck", *files],
        files=files,
    )
    result = EthosResult(
        command="quality shell",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command(name="toml")
def toml_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run TOML syntax and format checks through Taplo."""
    repo = _root(root)
    files = _git_files(repo, "*.toml")
    report = _quality_tool_report(
        root=repo,
        gate_id="toml-config",
        tool="taplo",
        command=["taplo", "check", *files],
        files=files,
    )
    result = EthosResult(
        command="quality toml",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command(name="yaml")
def yaml_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run YAML projection checks through yamllint."""
    repo = _root(root)
    files = _git_files(repo, "*.yml", "*.yaml")
    report = _quality_tool_report(
        root=repo,
        gate_id="yaml-config",
        tool="yamllint",
        command=["yamllint", "-d", "{extends: relaxed, rules: {line-length: disable}}", *files],
        files=files,
    )
    result = EthosResult(
        command="quality yaml",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command(name="code-size")
def code_size(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check effective source-file size against ratchet limits."""
    repo = _root(root)
    report = _code_size_report(repo)
    result = EthosResult(
        command="quality code-size",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command(name="npm")
def npm_quality(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Run npm distribution pack smoke checks without publishing."""
    repo = _root(root)
    files = ["package.json"] if (repo / "package.json").exists() else []
    report = _quality_tool_report(
        root=repo,
        gate_id="npm-pack",
        tool="npm",
        command=["npm", "run", "test:npm"],
        files=files,
    )
    result = EthosResult(
        command="quality npm",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


def _rule_fact_snapshot(
    repo: Path,
    *,
    phase: str,
    head: str,
    changed_paths: tuple[str, ...] = (),
    mutation: bool = False,
    authorized: bool = False,
    actor: str = "local",
    scope: str = "repository",
    status_payload: dict[str, object] | None = None,
    prewrite_report: dict[str, object] | None = None,
    audit_payload: dict[str, object] | None = None,
) -> RuleFactSnapshot:
    return _plan.rule_fact_snapshot(
        repo,
        phase=phase,
        head=head,
        changed_paths=changed_paths,
        mutation=mutation,
        authorized=authorized,
        actor=actor,
        scope=scope,
        status_payload=status_payload,
        prewrite_report=prewrite_report,
        audit_payload=audit_payload,
    )


def _rule_attestation_for_evaluation(
    evaluation: dict[str, object],
    *,
    actor: str,
    scope: str,
) -> dict[str, object]:
    attestation = RuleAttestation(
        head=str(evaluation["head"]),
        evaluation_digest=str(evaluation["digest"]),
        rule_set_digest=str(evaluation["rule_set_digest"]),
        compiled_policy_digest=str(evaluation["compiled_policy_digest"]),
        fact_snapshot_digest=str(evaluation["fact_snapshot_digest"]),
        actor=actor,
        scope=scope,
        runner_identity="ethos-cli",
        input=dict(evaluation["input_snapshot"]),
        output={
            "state": evaluation["state"],
            "required_gaps": list(evaluation["required_gaps"]),
            "required_gates": list(evaluation["required_gates"]),
        },
    )
    return attestation.to_dict()


@rules_app.command(name="check")
def rules_check(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check Rules Product Kernel readiness."""
    repo = _root(root)
    report = rules_check_report(repo)
    result = EthosResult(
        command="rules check",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        summary={
            "coverage_tier": report["coverage_tier"],
            "rule_count": len(report["resolved_rules"]),
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=tuple(report["next_action_contract"]),
        data=report,
    )
    _emit(result, json_output)


@rules_app.command(name="eval")
def rules_eval(
    *,
    root: RootOption | None = None,
    phase: str = "plan",
    changed_path: tuple[str, ...] = (),
    mutation: bool = False,
    authorized: bool = False,
    actor: str = "local",
    scope: str = "repository",
    json_output: JsonFlag = False,
) -> None:
    """Evaluate repository rules for a phase."""
    repo = _root(root)
    current_head = _current_head(repo)
    report = rules_evaluation_report(
        repo,
        phase=phase,
        changed_paths=tuple(changed_path),
        mutation=mutation,
        authorized=authorized,
        actor=actor,
        scope=scope,
        head=current_head,
        fact_snapshot=_rule_fact_snapshot(
            repo,
            phase=phase,
            changed_paths=tuple(changed_path),
            mutation=mutation,
            authorized=authorized,
            actor=actor,
            scope=scope,
            head=current_head,
        ),
    )
    attestation = _rule_attestation_for_evaluation(report, actor=actor, scope=scope)
    result = EthosResult(
        command="rules eval",
        ok=not report["required_gaps"],
        state="blocked" if report["state"] == "block" else str(report["state"]),
        summary={
            "phase": phase,
            "digest": report["digest"],
            "attestation": attestation,
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=tuple(report["next_action_contract"]),
        data=report,
    )
    _emit(result, json_output)


@rules_app.command(name="coverage")
def rules_coverage(
    *,
    root: RootOption | None = None,
    changed: bool = False,
    changed_path: tuple[str, ...] = (),
    json_output: JsonFlag = False,
) -> None:
    """Report changed-path rule coverage."""
    repo = _root(root)
    paths = tuple(workspace_status(repo)["changed_paths"]) if changed else tuple(changed_path)
    report = coverage_report(repo, changed_paths=paths)
    result = EthosResult(
        command="rules coverage",
        ok=bool(report["ok"]),
        state="covered" if report["ok"] else "gapped",
        summary={
            "covered_path_count": len(report["covered_paths"]),
            "uncovered_path_count": len(report["uncovered_paths"]),
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=tuple(report["next_action_contract"]),
        data=report,
    )
    _emit(result, json_output)


@rules_app.command(name="compile")
def rules_compile(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Compile repository rules deterministically."""
    repo = _root(root)
    report = compile_rules(repo)
    result = EthosResult(
        command="rules compile",
        ok=True,
        state="compiled",
        summary={"rule_count": len(report["rules"])},
        data=report,
    )
    _emit(result, json_output)


@rules_app.command(name="explain")
def rules_explain(
    target: str,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Explain a rule, gap, or path."""
    repo = _root(root)
    report = explain_rules_target(repo, target)
    result = EthosResult(
        command="rules explain",
        ok=True,
        state="explained",
        summary={"target": target},
        next_actions=tuple(report["next_action_contract"]),
        data=report,
    )
    _emit(result, json_output)


@rules_app.command(name="exceptions")
def rules_exceptions(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """List policy exceptions."""
    report = policy_exceptions_report(_root(root))
    result = EthosResult(
        command="rules exceptions",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command
def command_surface(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate public command surface vocabulary."""
    repo = _root(root)
    report = command_registry_report(repo)
    result = EthosResult(
        command="quality command-surface",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command
def format_policy(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report format-policy readiness."""
    repo = _root(root)
    policy_path = repo / ".ethos" / "rules.toml"
    if policy_path.exists():
        policy = tomllib.loads(policy_path.read_text(encoding="utf-8"))
        gaps: tuple[str, ...] = ()
    else:
        policy = {}
        gaps = ("format_policy_missing:.ethos/rules.toml",)
    result = EthosResult(
        command="quality format-policy",
        ok=not gaps,
        state="clean" if not gaps else "blocked",
        required_gaps=gaps,
        data={
            "source": ".ethos/rules.toml",
            "formats": policy.get("formats", {}),
            "artifacts": policy.get("artifacts", {}),
            "determinism": policy.get("determinism", {}),
            "standards": policy.get("standards", {}),
        },
    )
    _emit(result, json_output)


@quality_app.command
def projection_drift(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report projection drift readiness."""
    repo = _root(root)
    contract = projection_contract()
    playbooks = playbooks_report(repo, mode="v2-strict")
    registry_meta = playbooks["registry"]["meta"]
    registry_digest = str(playbooks["registry"]["digest"])
    expected_registry_digest = str(registry_meta.get("expected_registry_digest") or "")
    generator_digest = _sha256_file(Path(playbooks_module.__file__))
    expected_generator_digest = str(registry_meta.get("expected_generator_digest") or "")
    activation_digest = _sha256_file(repo / ".agents" / "skills" / "activation.toml")
    drift = [
        {"kind": "skill_package", "gap": gap}
        for gap in playbooks["required_gaps"]
        if str(gap).startswith("skill_package_")
    ]
    if not expected_registry_digest:
        drift.append({"kind": "skill_registry", "gap": "skill_registry_expected_digest_missing"})
    elif expected_registry_digest != registry_digest:
        drift.append({"kind": "skill_registry", "gap": "skill_registry_digest_mismatch"})
    if not expected_generator_digest:
        drift.append(
            {"kind": "projection_generator", "gap": "projection_generator_expected_digest_missing"}
        )
    elif expected_generator_digest != generator_digest:
        drift.append(
            {"kind": "projection_generator", "gap": "projection_generator_digest_mismatch"}
        )
    ok = contract["truth"] == ASSISTANT_TRUTH_BOUNDARY and not drift
    result = EthosResult(
        command="quality projection-drift",
        ok=ok,
        state="clean" if ok else "blocked",
        required_gaps=tuple(item["gap"] for item in drift)
        if contract["truth"] == ASSISTANT_TRUTH_BOUNDARY
        else ("assistant_projection_truth_drift",),
        data={
            "contract": contract,
            "drift": drift,
            "registry_digest": registry_digest,
            "registry": {
                "digest": registry_digest,
                "expected_digest": expected_registry_digest,
                "ok": expected_registry_digest == registry_digest,
            },
            "generator": {
                "id": "ethos_assistants.playbooks",
                "digest": generator_digest,
                "expected_digest": expected_generator_digest,
                "ok": expected_generator_digest == generator_digest,
            },
            "inputs": [
                {
                    "path": ".agents/skills/activation.toml",
                    "digest": activation_digest,
                }
            ],
        },
    )
    _emit(result, json_output)


@quality_app.command
def standards(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report standards and framework adapter registry."""
    registry = standard_adapter_registry()
    result = EthosResult(
        command="quality standards",
        ok=True,
        state="clean",
        data={"adapters": registry},
    )
    _emit(result, json_output)


@quality_app.command(name="package-ontology")
def package_ontology(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report target package ontology and migration-host state."""
    repo = _root(root)
    contract = package_ontology_report()
    target_missing = [
        f"packages/{package}"
        for package in contract["target_packages"]
        if not (repo / "packages" / str(package)).exists()
    ]
    host_missing = [
        f"packages/{package}"
        for package in contract["migration_hosts"]
        if not (repo / "packages" / str(package)).exists()
    ]
    distribution_missing = [
        distribution
        for distribution in contract["target_distributions"]
        if not (repo / str(distribution)).exists()
    ]
    workspace_config = workspace_package_config_report(repo)
    workspace_config_gaps = [str(gap) for gap in workspace_config["required_gaps"]]
    migration_complete = not contract["migration_hosts"] and all(
        item.get("state") == "migrated"
        for item in contract["migration_distributions"].values()
        if isinstance(item, dict)
    )
    physical_missing = target_missing + host_missing + distribution_missing
    data = {
        **contract,
        "physical_target_homes_present": not target_missing and not distribution_missing,
        "migration_complete": migration_complete,
        "migration_status": "complete" if migration_complete else "in_progress",
        "missing": physical_missing + workspace_config_gaps,
        "distribution_status": contract["migration_distributions"],
        "workspace_config": workspace_config,
    }
    result = EthosResult(
        command="quality package-ontology",
        ok=not data["missing"],
        state="tracked" if not data["missing"] else "gapped",
        summary={
            "target_package_count": len(contract["target_packages"]),
            "migration_host_count": len(contract["migration_hosts"]),
            "migration_status": data["migration_status"],
        },
        required_gaps=tuple(
            [f"package_ontology_missing:{item}" for item in physical_missing]
            + workspace_config_gaps
        ),
        next_actions=("ethos repository audit",),
        data=data,
    )
    _emit(result, json_output)


@quality_app.command
def schemas(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate ETHOS JSON Schemas."""
    repo = _root(root)
    report = schema_validation_report(repo)
    result = EthosResult(
        command="quality schemas",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command
def gates(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report executable proof gate registry."""
    registry = gate_registry()
    result = EthosResult(
        command="quality gates",
        ok=True,
        state="ready",
        summary={"gate_count": len(registry)},
        data={
            "gates": {
                gate_id: {
                    "kind": gate.kind,
                    "command": list(gate.command),
                    "policy": gate.policy,
                    "profile": gate.profile,
                    "toolchain": gate.toolchain,
                    "asset_classes": list(gate.asset_classes),
                    "dimensions": list(gate.dimensions),
                    "execution_mode": gate.execution_mode,
                    "evidence_class": gate.evidence_class,
                    "trust_bearing": gate.trust_bearing,
                    "tool_adapter": gate.tool_adapter,
                    "writes_files": gate.writes_files,
                    "network_policy": gate.network_policy,
                    "version_source": gate.version_source,
                    "depends_on": list(gate.depends_on),
                }
                for gate_id, gate in registry.items()
            }
        },
    )
    _emit(result, json_output)


@quality_app.command(name="coupling-audit")
def coupling_audit(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report product, profile, adapter, and product-toolchain coupling boundaries."""
    repo = _root(root)
    report = coupling_audit_report(repo)
    validation = _command_data_validation(
        repo,
        schema_name="coupling-audit.schema.json",
        payload=report,
    )
    validation_gaps = tuple(
        f"coupling_audit_schema:{gap}" for gap in validation["required_gaps"]
    )
    ok = bool(report["ok"]) and bool(validation["ok"])
    result = EthosResult(
        command="quality coupling-audit",
        ok=ok,
        state="clean" if ok else "blocked",
        diagnostics=(validation,),
        required_gaps=tuple(report["required_gaps"]) + validation_gaps,
        data=report,
    )
    _emit(result, json_output)


@quality_app.command
def commits(
    *,
    enforce_head: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report commit naming and signature policy."""
    repo = _root(root)
    report = signature_policy_report(repo)
    gaps = list(report["required_gaps"])
    if enforce_head and not report["head_subject_ok"]:
        gaps.append("head_subject_not_conventional")
    if enforce_head and not report["head_signature_ok"]:
        gaps.append("head_signature_not_good")
    result = EthosResult(
        command="quality commits",
        ok=not gaps,
        state="clean" if not gaps else "blocked",
        required_gaps=tuple(gaps),
        data={**report, "enforce_head": enforce_head},
    )
    _emit(result, json_output)


@quality_app.command
def release(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report product release surface and host-profile readiness."""
    repo = _root(root)
    release_files = repository_audit_module.release_files_report(repo)
    policy = release_policy_report(repo)
    result = EthosResult(
        command="quality release",
        ok=bool(release_files["ok"]),
        state="ready" if release_files["ok"] else "blocked",
        required_gaps=tuple(release_files["missing"]),
        next_actions=("uv build --all-packages",),
        data={
            "release_files": release_files,
            "host_profile": policy["host_profile"],
        },
    )
    _emit(result, json_output)


@quality_app.command
def release_policy(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate release version, host profile, protection, and attestation policy."""
    repo = _root(root)
    report = release_policy_report(repo)
    result = EthosResult(
        command="quality release-policy",
        ok=bool(report["ok"]),
        state="ready" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos quality release-attestation",),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command
def sbom(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit an SPDX-lite SBOM projection from workspace metadata."""
    repo = _root(root)
    projection = sbom_projection(repo)
    result = EthosResult(
        command="quality sbom",
        ok=True,
        state="ready",
        summary={"package_count": len(projection["packages"])},
        data={"sbom": projection},
    )
    _emit(result, json_output)


@quality_app.command(name="release-attestation")
def release_attestation_command(
    *,
    evidence_digest: str = "planned",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit release attestation envelope without publishing it."""
    repo = _root(root)
    attestation = release_attestation(
        root=repo,
        head=_current_head(repo),
        evidence_digest=evidence_digest,
    )
    result = EthosResult(
        command="quality release-attestation",
        ok=True,
        state="ready",
        summary={"tag": attestation["predicate"]["tag"]},
        data={"attestation": attestation},
    )
    _emit(result, json_output)


@quality_app.command
def command_registry(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate public command registry."""
    repo = _root(root)
    report = command_registry_report(repo)
    result = EthosResult(
        command="quality command-registry",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos repository audit",),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command
def evidence_freshness(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check declared evidence roots and claim digests."""
    repo = _root(root)
    claim_report = claims_report(repo)
    result = EthosResult(
        command="quality evidence-freshness",
        ok=bool(claim_report["ok"]),
        state="clean" if claim_report["ok"] else "blocked",
        summary={"evidence_roots": ["docs/evidence"]},
        required_gaps=tuple(claim_report["required_gaps"]),
        next_actions=("ethos prove --json",),
        data={"stale": [], "claims": claim_report},
    )
    _emit(result, json_output)


@quality_app.command
def claims(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate claim evidence digests."""
    repo = _root(root)
    report = claims_report(repo)
    result = EthosResult(
        command="quality claims",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos prove --json",),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command
def docs_registry(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate documentation metadata registry."""
    repo = _root(root)
    report = docs_health_report(repo)
    result = EthosResult(
        command="quality docs-registry",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos docs",),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command
def command_examples(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate documented command examples."""
    repo = _root(root)
    report = command_examples_report(repo)
    result = EthosResult(
        command="quality command-examples",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


@quality_app.command
def provenance(
    *,
    objective: str = "ethos provenance",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit a provenance envelope for a planned ETHOS proof."""
    repo = _root(root)
    run = ProofRun(
        action_id="planned-proof",
        command=("ethos", "prove", "--json"),
        exit_code=None,
        stdout="",
        stderr="",
        state="planned",
    )
    evidence = EvidenceSet.from_runs(
        id=f"ethos:{objective}",
        head=_current_head(repo),
        runs=(run,),
        durability="local",
    )
    result = EthosResult(
        command="quality provenance",
        ok=True,
        state="ready",
        summary={"evidence_digest": evidence.digest},
        next_actions=("ethos prove --json",),
        data={"evidence": evidence.to_dict(), "provenance": provenance_envelope(evidence)},
    )
    _emit(result, json_output)


@app.command(show=False)
def audit(
    *,
    mode: str = "deep",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Audit repository governance against the active profile."""
    repo = _root(root)
    if mode not in {"shape", "deep"}:
        result = EthosResult(
            command="audit",
            ok=False,
            state="invalid",
            required_gaps=(f"invalid_audit_mode:{mode}",),
            next_actions=("ethos audit --mode shape", "ethos audit --mode deep"),
            data={"mode": mode, "allowed_modes": ["shape", "deep"]},
        )
        _emit(result, json_output)
        return
    audit_payload = _audit_for_root(repo, openspec_mode=mode)
    result = EthosResult(
        command="audit",
        ok=bool(audit_payload["ok"]),
        state="clean" if audit_payload["ok"] else "gapped",
        summary={"openspec_mode": mode},
        required_gaps=tuple(audit_payload["required_gaps"]),
        next_actions=("ethos report",) if audit_payload["ok"] else ("ethos audit --mode deep",),
        data=audit_payload,
    )
    _emit(result, json_output)


@app.command(show=False)
def openspec(
    *,
    change: str | None = None,
    lifecycle: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Audit official OpenSpec governance state."""
    repo = _root(root)
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
    _emit(result, json_output)


@campaign_app.command(name="status")
def campaign_status(
    *,
    campaign: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report canonical campaign model."""
    repo = _root(root)
    report = campaign_report(repo, campaign_id=campaign)
    result = EthosResult(
        command="campaign status",
        ok=bool(report["ok"]),
        state="active",
        summary={
            "active_campaign_count": report["active_count"],
            "campaign_count": report["campaign_count"],
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos campaign closeout --json",),
        data=report,
    )
    _emit(result, json_output)


@campaign_app.command
def hypotheses(*, json_output: JsonFlag = False) -> None:
    """List active ETHOS evolution hypotheses."""
    ledger = evolution_ledger(Path.cwd())
    result = EthosResult(
        command="campaign hypotheses",
        ok=True,
        state="active",
        summary={"campaign": "ethos-product-maturation"},
        next_actions=("ethos audit --mode shape",),
        data=ledger,
    )
    _emit(result, json_output)


@campaign_app.command(name="closeout")
def campaign_closeout(
    *,
    adopter: str = "generic",
    target: Annotated[Path | None, Parameter(name="--target")] = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report the local campaign closeout package without publishing remotely."""
    repo = _root(root)
    report = _campaign_closeout_report(
        repo=repo,
        adopter=adopter,
        target=(target or repo).resolve(),
    )
    result = EthosResult(
        command="campaign closeout",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "adopter": adopter,
            "remote_state": report["remote_publication"]["state"],
            "parity_pending_count": len(report["parity"]["pending_packages"]),
            "release_ok": report["release"]["ok"],
        },
        required_gaps=tuple(report["evolution"]["required_gaps"])
        + tuple(report["release"]["required_gaps"]),
        next_actions=("ethos land --apply --authorize --expect-head <git-head>",),
        data=report,
    )
    _emit(result, json_output)


@assistants_app.command(name="doctor")
def assistants_doctor(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report assistant projection readiness."""
    _root(root)
    contract = projection_contract()
    result = EthosResult(
        command="assistants doctor",
        ok=True,
        state="ready",
        summary={"surface_count": len(contract["surfaces"])},
        next_actions=("ethos assistants mcp-manifest",),
        data={"contract": contract},
    )
    _emit(result, json_output)


@assistants_app.command
def check_projections(*, json_output: JsonFlag = False) -> None:
    """Check assistant projections stay thin."""
    contract = projection_contract()
    result = EthosResult(
        command="assistants check-projections",
        ok=contract["truth"] == ASSISTANT_TRUTH_BOUNDARY,
        state="clean",
        next_actions=("ethos quality projection-drift",),
        data={"contract": contract},
    )
    _emit(result, json_output)


@assistants_app.command(name="mcp-manifest")
def mcp_manifest_command(*, json_output: JsonFlag = False) -> None:
    """Emit ETHOS MCP projection manifest."""
    manifest = mcp_manifest()
    result = EthosResult(
        command="assistants mcp-manifest",
        ok=True,
        state="ready",
        summary={
            "resource_count": len(manifest["resources"]),
            "tool_count": len(manifest["tools"]),
        },
        next_actions=("ethos assistants check-projections",),
        data={"manifest": manifest},
    )
    _emit(result, json_output)


@assistants_app.command(name="mcp-server")
def mcp_server_command(*, json_output: JsonFlag = False) -> None:
    """Describe the ETHOS MCP server adapter."""
    descriptor = mcp_server_descriptor()
    result = EthosResult(
        command="assistants mcp-server",
        ok=True,
        state="ready",
        summary={"transport": descriptor["transport"]},
        next_actions=("ethos assistants mcp-manifest",),
        data={"server": descriptor},
    )
    _emit(result, json_output)


@assistants_app.command(name="context")
def assistants_context(
    *,
    root: RootOption | None = None,
    scope: str = "repo",
    query: str | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit the ETHOS agentic context bundle."""
    repo = _root(root)
    retrieval = search_context_index(repo, query) if query else None
    selection = retrieval["selection"] if retrieval else None
    bundle = context_bundle(query=query, selection=selection, scope=scope)
    result = EthosResult(
        command="assistants context",
        ok=bool(retrieval["ok"]) if retrieval else True,
        state=str(retrieval["state"]) if retrieval else "ready",
        summary={
            "protocol_count": len(bundle["protocols"]),
            "verified_count": retrieval["summary"]["verified_count"] if retrieval else 0,
        },
        required_gaps=tuple(retrieval["required_gaps"]) if retrieval else (),
        data={"context": bundle},
    )
    _emit(result, json_output)


@assistants_app.command(name="search")
def assistants_search(
    query: str,
    *,
    root: RootOption | None = None,
    limit: int = 10,
    json_output: JsonFlag = False,
) -> None:
    """Search the local source-verified context projection."""
    repo = _root(root)
    report = search_context_index(repo, query, limit=limit)
    result = EthosResult(
        command="assistants search",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=dict(report["summary"]),
        required_gaps=tuple(report["required_gaps"]),
        data={"selection": report["selection"]},
    )
    _emit(result, json_output)


@assistants_app.command(name="context-index")
def assistants_context_index(
    *,
    root: RootOption | None = None,
    apply: bool = False,
    authorize: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Build the local context projection index."""
    repo = _root(root)
    report = rebuild_context_index(repo, apply=apply, authorized=authorize)
    result = EthosResult(
        command="assistants context-index",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=dict(report["summary"]),
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos assistants search <query> --json",)
        if report["ok"] and report["state"] == "indexed"
        else (),
        data=dict(report.get("data", {})),
    )
    _emit(result, json_output)


@assistants_app.command(name="context-purge")
def assistants_context_purge(
    *,
    root: RootOption | None = None,
    apply: bool = False,
    authorize: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Purge the local context projection index."""
    repo = _root(root)
    report = purge_context_index(repo, apply=apply, authorized=authorize)
    result = EthosResult(
        command="assistants context-purge",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=dict(report["summary"]),
        required_gaps=tuple(report["required_gaps"]),
        data=dict(report.get("data", {})),
    )
    _emit(result, json_output)


@assistants_app.command(name="context-eval")
def assistants_context_eval(
    *,
    root: RootOption | None = None,
    suite: str = "smoke",
    json_output: JsonFlag = False,
) -> None:
    """Evaluate the local context projection index."""
    repo = _root(root)
    fixtures = context_retrieval_smoke_queries() if suite == "smoke" else ()
    report = context_eval_report(repo, suite=suite, fixtures=fixtures)
    result = EthosResult(
        command="assistants context-eval",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=dict(report["summary"]),
        required_gaps=tuple(report["required_gaps"]),
        data=dict(report.get("data", {})),
    )
    _emit(result, json_output)


@playbooks_app.command(name="check")
def playbooks_check(
    *,
    root: RootOption | None = None,
    mode: str = "v2-strict",
    json_output: JsonFlag = False,
) -> None:
    """Check repo-local ETHOS playbook projection."""
    repo = _root(root)
    report = playbooks_report(repo, mode=mode)
    result = EthosResult(
        command="playbooks check",
        ok=bool(report["ok"]),
        state="ready" if report["ok"] else "gapped",
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos playbooks route",),
        data=report,
    )
    _emit(result, json_output)


@playbooks_app.command(name="route")
def playbooks_route(
    *,
    subject: str = "repository-governance",
    changed: bool = False,
    root: RootOption | None = None,
    mode: str = "v2-strict",
    json_output: JsonFlag = False,
) -> None:
    """Route a subject to repo-local ETHOS playbooks."""
    repo = _root(root)
    route_subject = "changed-scope" if changed else subject
    changed_paths = tuple(workspace_status(repo)["changed_paths"]) if changed else ()
    report = route_playbook(
        repo,
        route_subject,
        require_explicit_subject=changed,
        mode=mode,
        changed_paths=changed_paths,
    )
    result = EthosResult(
        command="playbooks route",
        ok=bool(report["ok"]),
        state="routed" if report["ok"] else "gapped",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


@parity_app.command(name="ledger")
def parity_ledger(*, json_output: JsonFlag = False) -> None:
    """Emit the executable capability parity ledger."""
    report = parity_ledger_report()
    result = EthosResult(
        command="parity ledger",
        ok=bool(report["ok"]),
        state="classified",
        summary=report["summary"],
        next_actions=("ethos parity gaps --adopter <adopter>",),
        data={"records": report["records"]},
    )
    _emit(result, json_output)


@parity_app.command(name="gaps")
def parity_gaps(
    *,
    adopter: str | None = None,
    target: Path | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report remaining product/adopter parity gaps."""
    repo = _root(root)
    report = parity_gaps_report(
        adopter=adopter,
        root=repo,
        target=target,
        current_target_head=_current_tracked_head(target) if target is not None else "",
        current_product_head=_current_tracked_head(repo),
        acceptable_product_heads=_acceptable_parity_product_heads(repo, adopter),
        acceptable_target_heads=_acceptable_parity_target_heads(repo, target, adopter),
    )
    evidence = report.get("evidence") if isinstance(report.get("evidence"), dict) else {}
    refresh = evidence.get("refresh_package") if isinstance(evidence, dict) else None
    refresh_command = (
        str(refresh["command"]) if isinstance(refresh, dict) and refresh.get("command") else ""
    )
    result = EthosResult(
        command="parity gaps",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "gapped",
        summary={"adopter": report["adopter"], "gap_count": len(report["required_gaps"])},
        required_gaps=tuple(report["required_gaps"]),
        next_actions=(
            (
                refresh_command
                or (
                    "ethos parity shadow --adopter <adopter-id> --target <repo> "
                    "--execute --write-evidence"
                ),
            )
            if report["required_gaps"]
            else ("ethos prove --full",)
        ),
        data=report,
    )
    _emit(result, json_output)


@parity_app.command(name="shadow")
def parity_shadow(
    *,
    target: Path,
    adopter: str | None = None,
    execute: bool = False,
    write_evidence: bool = False,
    timeout_seconds: int = 30,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Plan an external shadow parity comparison for an adopter."""
    repo = _root(root)
    adopter_name = adopter or "generic"
    if execute:
        from ethos_adapters.shadow import run_shadow_parity

        report = run_shadow_parity(target=target, timeout_seconds=timeout_seconds)
    else:
        report = shadow_parity_report(
            target=target,
            root=repo,
            adopter=adopter,
            current_target_head=_current_tracked_head(target),
            current_product_head=_current_tracked_head(repo),
            acceptable_product_heads=_acceptable_parity_product_heads(repo, adopter),
            acceptable_target_heads=_acceptable_parity_target_heads(repo, target, adopter),
        )
    required_gaps = list(report["required_gaps"])
    evidence_path = ""
    if write_evidence:
        if not execute:
            required_gaps.append("parity_evidence_write_requires_execute")
        elif report.get("ok") is not True:
            required_gaps.append(f"parity_evidence_write_blocked:{adopter_name}")
        else:
            evidence = build_tracked_parity_evidence(
                adopter=adopter_name,
                target=target,
                shadow=report,
                current_product_head=_current_tracked_head(repo),
                current_target_head=_current_tracked_head(target),
                timeout_seconds=timeout_seconds,
            )
            written = write_tracked_parity_evidence(
                root=repo,
                adopter=adopter_name,
                evidence=evidence,
            )
            evidence_path = written.relative_to(repo).as_posix()
            report = {**report, "evidence_written": evidence_path}
    result = EthosResult(
        command="parity shadow",
        ok=bool(report["ok"]) and not required_gaps,
        state=str(report["state"]),
        required_gaps=tuple(required_gaps),
        next_actions=("ethos prove --full",) if not required_gaps else ("ethos parity gaps",),
        data=report,
    )
    _emit(result, json_output)


@app.command
def report(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit a concise scorecard."""
    repo = _root(root)
    audit = _audit_for_root(repo, openspec_mode="shape")
    docs_report = docs_health_report(repo)
    claim_report = claims_report(repo)
    command_report = command_registry_report(repo)
    projection = projection_contract()
    schemas_report = schema_validation_report(repo)
    evolution = evolution_report(repo)
    signature = signature_policy_report(repo)
    audit_profile = str(audit["governance_context"]["profile"])
    product_profile = audit_profile == "product"
    playbooks = playbooks_report(repo, mode="v2-strict")
    adoption_scaffold = adoption_scaffold_report()
    parity_ledger = parity_ledger_report()
    parity_gaps = parity_gaps_report(
        root=repo,
        current_product_head=_current_tracked_head(repo),
        acceptable_product_heads=_acceptable_parity_product_heads(repo, None),
    )
    context_projection = context_projection_contract()
    context_projection_score = int(
        context_projection["authority"] == "projection"
        and not context_projection["can_close_required_gaps"]
        and not context_projection["can_satisfy_proof"]
    )
    if not product_profile:
        scores = {
            "adopter_governance": int(bool(audit["ok"])),
            "schemas": int(bool(audit["schemas"]["ok"])),
            "claims": int(bool(audit["adopter"]["adopter"]["governance"]["claims"])),
            "docs": int(bool(audit["adopter"]["adopter"]["governance"]["docs"])),
            "assistant_projection": int(projection["truth"] == ASSISTANT_TRUTH_BOUNDARY),
            "context_projection": context_projection_score,
            "playbooks": int(bool(playbooks["ok"])),
            "parity_ledger": int(bool(parity_ledger["ok"])),
        }
    else:
        scores = {
            "package_ontology": int(bool(audit["package_ontology"]["ok"])),
            "distribution_adapter": int(not audit["package_ontology"]["adapter_missing"]),
            "docs": int(bool(docs_report["ok"])),
            "schemas": int(bool(audit["schemas"]["ok"])),
            "schema_validation": int(bool(schemas_report["ok"])),
            "claims": int(bool(claim_report["ok"])),
            "command_registry": int(bool(command_report["ok"])),
            "standards": int(
                all(
                    item["boundary"] and item["fallback"] and item["exit_strategy"]
                    for item in standard_adapter_registry().values()
                )
            ),
            "assistant_projection": int(projection["truth"] == ASSISTANT_TRUTH_BOUNDARY),
            "context_projection": context_projection_score,
            "evolution": int(bool(evolution["ok"])),
            "signature_policy": int(bool(signature["ok"])),
            "openspec": int(bool(audit["openspec"]["ok"])),
            "playbooks": int(bool(playbooks["ok"])),
            "adoption_scaffold": int(bool(adoption_scaffold["ok"])),
            "parity_ledger": int(bool(parity_ledger["ok"])),
        }
    ok = all(value == 1 for value in scores.values())
    parity_pending_count = len(parity_gaps["required_gaps"])
    result_required_gaps = tuple(audit["required_gaps"])
    if product_profile:
        result_required_gaps = result_required_gaps + tuple(claim_report["required_gaps"])
    first_hour = {}
    if not product_profile:
        evidence_gap_count = len(result_required_gaps)
        readiness = "local_readiness" if evidence_gap_count == 0 else "blocked"
        first_hour = {
            "proof_status": "ready" if evidence_gap_count == 0 else "gapped",
            "evidence_gap_count": evidence_gap_count,
            "land_readiness": readiness,
            "publish_readiness": readiness,
            "hosted_ci_truth": "external-evidence",
            "next_action": "ethos prove" if evidence_gap_count == 0 else "resolve evidence gaps",
        }
    gap_layers = {
        "governance_audit": {
            "scope": "governance_audit",
            "blocking": True,
            "ok": not result_required_gaps,
            "required_gaps": list(result_required_gaps),
            "gap_count": len(result_required_gaps),
        },
        "capability_parity": {
            "scope": "capability_parity",
            "blocking": False,
            "ok": bool(parity_gaps["ok"]),
            "required_gaps": list(parity_gaps["required_gaps"]),
            "gap_count": parity_pending_count,
        },
        "playbook_projection": {
            "scope": "skills-v2",
            "blocking": True,
            "ok": bool(playbooks["ok"]),
            "required_gaps": list(playbooks["required_gaps"]),
            "advisory_gaps": list(playbooks["advisory_gaps"]),
            "gap_count": len(playbooks["required_gaps"]),
        },
    }
    scorecards = [
        {
            "id": "skills-v2",
            "scope": "playbook_projection",
            "mode": playbooks["mode"],
            "ok": bool(playbooks["ok"]),
            "score": playbooks["v2_compliance"]["score"],
            "max_score": playbooks["v2_compliance"]["max_score"],
            "blocking": True,
            "required_gaps": list(playbooks["required_gaps"]),
            "advisory_gaps": list(playbooks["advisory_gaps"]),
        }
    ]
    result = EthosResult(
        command="report",
        ok=ok,
        state="ready" if ok else "gapped",
        summary={
            "score": sum(scores.values()),
            "max_score": len(scores),
            "governance_gap_count": len(result_required_gaps),
            "parity_pending_count": parity_pending_count,
        },
        required_gaps=result_required_gaps,
        next_actions=(
            ("ethos parity gaps --adopter <adopter>",)
            if parity_pending_count
            else ("ethos prove --full",)
        ),
        data={
            "governance_context": audit["governance_context"],
            "scores": scores,
            "first_hour": first_hour,
            "scorecards": scorecards,
            "repository_audit": audit,
            "docs": docs_report,
            "claims": claim_report,
            "assistant_projection": projection,
            "context_projection": context_projection,
            "schema_validation": schemas_report,
            "evolution": evolution,
            "signature_policy": signature,
            "playbooks": playbooks,
            "adoption_scaffold": adoption_scaffold,
            "gap_layers": gap_layers,
            "parity": {
                "scope": {
                    "generic_gap_count": parity_pending_count,
                    "domain_profile_parity_closed": False,
                    "note": (
                        "Generic command parity does not claim domain profile parity "
                        "or adopter-specific retirement readiness."
                    ),
                },
                "ledger": parity_ledger,
                "gaps": parity_gaps,
            },
            "profiles": list(available_profiles()),
        },
    )
    _emit(result, json_output)


@app.command(show=False)
def explain(gap: str, *, json_output: JsonFlag = False) -> None:
    """Explain a required gap."""
    result = EthosResult(
        command="explain",
        ok=True,
        state="explained",
        summary={"gap": gap},
        data={"meaning": "A required gap names missing evidence, policy, schema, or action."},
    )
    _emit(result, json_output)


@app.command(show=False)
def docs(
    topic: str = "index",
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Locate documentation for a topic."""
    repo = _root(root)
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
    _emit(result, json_output)


def _repository_audit_after_admission(repo: Path, decision: MutationDecision) -> dict[str, object]:
    if not decision.ok:
        return {
            "ok": False,
            "state": "skipped",
            "reason": "mutation_admission_blocked",
            "required_gaps": [],
            "root": repo.as_posix(),
        }
    return _audit_for_root(repo, openspec_mode="shape")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
