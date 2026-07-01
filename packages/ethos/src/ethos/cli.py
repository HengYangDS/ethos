from __future__ import annotations

import fnmatch
import subprocess
import tomllib
from pathlib import Path
from typing import Annotated

import ethos_governance.self_audit as self_audit_module
from cyclopts import App, Parameter
from ethos_agent.context import context_bundle
from ethos_agent.mcp import mcp_manifest
from ethos_agent.playbooks import playbooks_report, route_playbook
from ethos_agent.projections import projection_contract
from ethos_agent.server import mcp_server_descriptor
from ethos_contracts.package_ontology import package_ontology_report
from ethos_governance.attestation import release_attestation, sbom_projection
from ethos_governance.claims import claims_report
from ethos_governance.command_registry import command_registry_report
from ethos_governance.commit_policy import signature_policy_report
from ethos_governance.docs_registry import (
    build_docs_registry,
    command_examples_report,
    docs_health_report,
)
from ethos_governance.evidence import EvidenceSet, ProofRun, provenance_envelope, trim_output
from ethos_governance.evolution import evolution_candidates, evolution_ledger, evolution_report
from ethos_governance.gates import gate_graph, gate_registry
from ethos_governance.openspec_native import openspec_self_governance_report
from ethos_governance.release import release_policy_report
from ethos_governance.schema_validation import schema_validation_report, validate_schema_instance
from ethos_governance.standards import standard_adapter_registry
from ethos_kernel.action_graph import ActionGraph, ActionNode
from ethos_kernel.result import EthosResult
from ethos_project.fleet import inspect_adopter
from ethos_project.planner import adoption_plan, adoption_scaffold_report, available_profiles
from ethos_repository.parity import parity_gaps_report, parity_ledger_report, shadow_parity_report
from ethos_workspace.lanes import (
    bootstrap_candidate,
    retire_landed_work_lanes,
    start_work_lane,
)
from ethos_workspace.mutation import (
    MutationDecision,
    MutationRequest,
    apply_land_to_candidate,
    evaluate_mutation,
)
from ethos_workspace.prewrite import prewrite_guard
from ethos_workspace.runner import DryRunRunner, LocalSubprocessRunner
from ethos_workspace.state import initialize_state
from ethos_workspace.status import workspace_status

app = App(name="ethos", help="ETHOS command plane.")
quality_app = App(name="quality", help="Quality and determinism checks.")
self_app = App(name="self", help="Self-governance commands.")
campaign_app = App(name="campaign", help="Evolution campaign commands.")
intake_app = App(name="intake", help="Intake ledger commands.")
assistants_app = App(name="assistants", help="Assistant and protocol projections.")
playbooks_app = App(name="playbooks", help="Repo-local skills and playbook routing.")
fleet_app = App(name="fleet", help="External adopter and fleet inspection.")
lane_app = App(name="lane", help="Work Lane lifecycle and write admission.")
parity_app = App(name="parity", help="Capability parity and adopter shadow checks.")
app.command(quality_app)
app.command(self_app)
app.command(campaign_app)
app.command(intake_app)
app.command(assistants_app)
app.command(playbooks_app)
app.command(fleet_app)
app.command(lane_app)
app.command(parity_app)


JsonFlag = Annotated[bool, Parameter(name="--json")]
RootOption = Annotated[Path, Parameter(name="--root")]


def _root(root: Path | None) -> Path:
    return (root or Path.cwd()).resolve()


def _current_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return "untracked"
    return completed.stdout.strip()


def _emit(result: EthosResult, json_output: bool) -> None:
    if json_output:
        print(result.to_json())
        return
    print(f"{result.command}: {result.state}")
    for action in result.next_actions:
        print(f"next: {action}")


def _graph_for_paths(paths: tuple[str, ...]) -> ActionGraph:
    inputs = tuple(sorted(paths)) or ("pyproject.toml",)
    nodes = (
        ActionNode(
            id="status",
            kind="inspection",
            command=("ethos", "status", "--json"),
            inputs=inputs,
            outputs=(),
            policy="required",
        ),
        ActionNode(
            id="prove",
            kind="proof",
            command=("ethos", "prove", "--json"),
            inputs=inputs,
            outputs=("docs/evidence/latest-proof.json",),
            policy="required",
        ),
        ActionNode(
            id="self-audit",
            kind="governance",
            command=("ethos", "self", "audit", "--json"),
            inputs=inputs,
            outputs=(),
            policy="required",
        ),
    )
    return ActionGraph(nodes=nodes)


def _rules_config(root: Path) -> dict[str, object]:
    path = root / ".ethos" / "rules.toml"
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _is_product_root(root: Path) -> bool:
    return (
        (root / "packages" / "ethos" / "README.md").exists()
        and (root / "schemas" / "ethos").exists()
    )


def _audit_for_root(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
    if _is_product_root(root):
        return self_audit_module.self_audit(root, openspec_mode=openspec_mode)
    return _adopter_audit(root)


def _adopter_audit(root: Path) -> dict[str, object]:
    adopter = inspect_adopter(root)
    schemas = schema_validation_report(root)
    claims = claims_report(root)
    docs = docs_health_report(root)
    gaps = (
        list(adopter["required_gaps"])
        + [f"schema:{gap}" for gap in schemas["required_gaps"]]
    )
    return {
        "ok": not gaps,
        "mode": "adopter",
        "required_gaps": gaps,
        "adopter": adopter,
        "schemas": {
            "ok": bool(schemas["ok"]),
            "validation": schemas,
            "missing": [],
        },
        "claims": claims,
        "docs": docs,
        "openspec": {
            "ok": bool(adopter["adopter"]["governance"]["openspec"]),
            "mode": "adopter-shape",
            "required_gaps": []
            if adopter["adopter"]["governance"]["openspec"]
            else ["adopter_missing:openspec"],
        },
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _path_matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(f"{prefix}/")
    return fnmatch.fnmatchcase(path, pattern)


def _matching_rule_gates(
    root: Path,
    paths: tuple[str, ...],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    config = _rules_config(root)
    gates = config.get("gates") if isinstance(config.get("gates"), dict) else {}
    matched_rules: list[dict[str, object]] = []
    required_gates: list[dict[str, object]] = []
    rules = config.get("rule") if isinstance(config.get("rule"), list) else []
    for raw_rule in rules:
        if not isinstance(raw_rule, dict):
            continue
        matched_paths = [
            path
            for path in paths
            if any(_path_matches(path, pattern) for pattern in _string_list(raw_rule.get("paths")))
        ]
        if not matched_paths:
            continue
        rule_gates: list[dict[str, object]] = []
        for gate_id in _string_list(raw_rule.get("requires")):
            gate_config = gates.get(gate_id, {}) if isinstance(gates, dict) else {}
            gate = {
                "id": gate_id,
                "command": (
                    str(gate_config.get("command", "")) if isinstance(gate_config, dict) else ""
                ),
                "blocking": gate_config.get("blocking", True) is not False
                if isinstance(gate_config, dict)
                else True,
            }
            rule_gates.append(gate)
            required_gates.append(gate)
        matched_rules.append(
            {
                "id": str(raw_rule.get("id", "")),
                "risk": str(raw_rule.get("risk", "")),
                "matched_paths": matched_paths,
                "required_gates": rule_gates,
                "evidence": _string_list(raw_rule.get("evidence")),
            }
        )
    return matched_rules, required_gates


def _workspace_status_validation(repo: Path, payload: dict[str, object]) -> dict[str, object]:
    validation = validate_schema_instance("workspace-status.schema.json", payload, root=repo)
    return {
        "kind": "schema_validation",
        "target": "data",
        "schema": "workspace-status.schema.json",
        "ok": bool(validation["ok"]),
        "required_gaps": list(validation["required_gaps"]),
    }


def _workspace_status_validation_gaps(validation: dict[str, object]) -> tuple[str, ...]:
    return tuple(f"workspace_status_schema:{gap}" for gap in validation["required_gaps"])


def _local_submit_package(*, branch: str, submit_branch: str) -> dict[str, object]:
    return {
        "kind": "submit_branch_plan",
        "source_branch": branch,
        "submit_branch": submit_branch,
        "remote_push": "not_performed",
        "remote_state": "deferred",
        "blocking": False,
        "required_steps": [
            "land work lane to candidate/dev",
            "fast-forward local dev from candidate/dev",
            "create submit/* and push when remote publication is available",
        ],
    }


def _publication_readiness(*, branch: str, local_ok: bool) -> dict[str, object]:
    submit_branch = f"submit/{branch.removeprefix('work/')}" if branch.startswith("work/") else ""
    return {
        "mode": "local_readiness",
        "remote_push": "not_performed",
        "remote_state": "deferred",
        "submit_branch": submit_branch,
        "local_submit_package": _local_submit_package(
            branch=branch,
            submit_branch=submit_branch,
        ),
        "required_gaps": [] if local_ok else ["local_publish_readiness_blocked"],
        "next_actions": (
            ["create submit/* and push when remote publication is available"]
            if local_ok
            else ["resolve local publish readiness gaps"]
        ),
    }


def _remote_publication_deferred() -> dict[str, object]:
    return {
        "remote_push": "not_performed",
        "state": "deferred",
        "reason": "remote publication adapter unavailable",
    }


def _campaign_closeout_report(
    *,
    repo: Path,
    adopter: str,
    target: Path,
) -> dict[str, object]:
    status_payload = workspace_status(repo)
    branch = str(status_payload["branch"])
    evolution = evolution_report(repo)
    release = release_policy_report(repo)
    parity = parity_gaps_report(adopter=adopter, root=repo)
    shadow = shadow_parity_report(target=target, root=repo, adopter=adopter)
    local_ready = bool(evolution["ok"]) and bool(release["ok"])
    publication = _publication_readiness(branch=branch, local_ok=local_ready)
    local_closeout = dict(status_payload["closeout_support"])
    local_closeout["kind"] = "local_closeout_plan"
    local_closeout["blocking"] = bool(local_closeout["required_gaps"])

    packages = {
        "local_closeout": local_closeout,
        "publication": publication,
        "release": {
            "kind": "release_policy",
            "ok": bool(release["ok"]),
            "version": release["version"],
            "required_gaps": list(release["required_gaps"]),
        },
        "parity": {
            "kind": "parity_backlog",
            "adopter": parity["adopter"],
            "pending_count": len(parity["pending_packages"]),
            "required_gaps": list(parity["required_gaps"]),
            "blocking": False,
        },
        "shadow_parity": shadow["execution_packages"][0],
    }
    return {
        "ok": local_ready,
        "state": "local_ready" if local_ready else "gapped",
        "workspace": status_payload,
        "evolution": evolution,
        "release": release,
        "parity": parity,
        "shadow_parity": shadow,
        "publication": publication,
        "remote_publication": _remote_publication_deferred(),
        "packages": packages,
    }


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
    _emit(result, json_output)


@lane_app.command
def start(
    name: str,
    *,
    path: Annotated[Path, Parameter(name="--path")],
    owner: str,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Start an owned Work Lane and acquire a local lease."""
    repo = _root(root)
    report = start_work_lane(root=repo, name=name, path=path, owner=owner, apply=apply)
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
            "landed_lane_count": sum(
                1 for lane in report["lanes"] if lane["retire_ready"]
            ),
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
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Produce a local proof-readiness summary."""
    repo = _root(root)
    audit = _audit_for_root(repo, openspec_mode="deep" if full else "shape")
    graph = gate_graph(gate, full=full)
    runner = LocalSubprocessRunner() if execute else DryRunRunner()
    proof_runs = tuple(
        ProofRun(
            action_id=run_result.action_id,
            command=run_result.command,
            exit_code=run_result.exit_code,
            stdout=trim_output(run_result.stdout),
            stderr=trim_output(run_result.stderr),
            state=run_result.state,
        )
        for run_result in (runner.run(node, root=repo) for node in graph.ordered_nodes())
    )
    evidence = EvidenceSet.from_runs(
        id=f"ethos:{objective}",
        head=_current_head(repo),
        runs=proof_runs,
        durability="local",
    )
    runs_ok = all(run.state in {"passed", "planned"} for run in proof_runs)
    proof_gaps: tuple[str, ...] = ("full_proof_requires_execute",) if full and not execute else ()
    ok = bool(audit["ok"]) and runs_ok and graph.validate().ok and not proof_gaps
    result = EthosResult(
        command="prove",
        ok=ok,
        state="proven" if ok else "gapped",
        summary={
            "objective": objective,
            "evidence_digest": evidence.digest,
            "gate_count": len(proof_runs),
        },
        required_gaps=(
            tuple(audit["required_gaps"]) + tuple(graph.validate().gaps) + proof_gaps
        ),
        next_actions=("ethos land",) if ok else ("ethos self audit",),
        data={
            "self_audit": audit,
            "executed": execute,
            "action_graph": graph.to_dict(),
            "evidence": evidence.to_dict(),
            "provenance": provenance_envelope(evidence),
        },
    )
    _emit(result, json_output)


@app.command
def land(
    *,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report land readiness."""
    repo = _root(root)
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
    audit = _self_audit_after_admission(repo, decision)
    gaps = tuple(audit["required_gaps"]) + decision.gaps
    ok = bool(audit["ok"]) and decision.ok
    candidate_update: dict[str, object] = {}
    if ok and apply:
        candidate_update = apply_land_to_candidate(
            root=repo,
            authorized=authorize,
            expect_head=expect_head,
        )
        gaps = gaps + tuple(candidate_update["required_gaps"])
        ok = bool(candidate_update["ok"])
    result = EthosResult(
        command="land",
        ok=ok,
        state=(
            "ready_to_land"
            if ok and not apply
            else str(candidate_update.get("state") or decision.state)
        ),
        required_gaps=gaps,
        next_actions=("ethos publish",) if ok else ("ethos prove --json",),
        data={
            "self_audit": audit,
            "candidate_update": candidate_update,
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
    audit = _self_audit_after_admission(repo, decision)
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
            "self_audit": audit,
            "remote_push": "not_performed",
            "publication": _publication_readiness(branch=str(branch), local_ok=ok),
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


@app.command
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
    profile: str | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Initialize ETHOS adoption for a repository."""
    target = _root(root)
    do_apply = apply
    plan_payload = adoption_plan(target, profile=profile, apply=do_apply)
    result = EthosResult(
        command="init",
        ok=True,
        state="applied" if do_apply else "planned",
        summary={"planned_file_count": len(plan_payload["planned_files"])},
        next_actions=("ethos status",),
        data=plan_payload,
    )
    _emit(result, json_output)


@app.command
def adopt(
    *,
    root: RootOption | None = None,
    dry_run: bool = True,
    apply: bool = False,
    profile: str | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Plan or apply ETHOS adoption for a repository."""
    target = _root(root)
    do_apply = apply
    plan_payload = adoption_plan(target, profile=profile, apply=do_apply)
    result = EthosResult(
        command="adopt",
        ok=True,
        state="applied" if do_apply else "planned",
        summary={"planned_file_count": len(plan_payload["planned_files"])},
        next_actions=("ethos status",),
        data=plan_payload,
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
    json_output: JsonFlag = False,
) -> None:
    """Report projection drift readiness."""
    contract = projection_contract()
    ok = contract["truth"] == "ethos-kernel-and-repository"
    result = EthosResult(
        command="quality projection-drift",
        ok=ok,
        state="clean" if ok else "blocked",
        required_gaps=() if ok else ("assistant_projection_truth_drift",),
        data={"contract": contract, "drift": []},
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
    data = {
        **contract,
        "physical_target_homes_present": not target_missing and not distribution_missing,
        "migration_complete": False,
        "migration_status": "in_progress",
        "missing": target_missing + host_missing + distribution_missing,
        "distribution_status": contract["migration_distributions"],
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
        required_gaps=tuple(f"package_ontology_missing:{item}" for item in data["missing"]),
        next_actions=("ethos self audit",),
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
                }
                for gate_id, gate in registry.items()
            }
        },
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
    """Report release and GitLab readiness."""
    repo = _root(root)
    release_files = self_audit_module.release_files_report(repo)
    result = EthosResult(
        command="quality release",
        ok=bool(release_files["ok"]),
        state="ready" if release_files["ok"] else "blocked",
        required_gaps=tuple(release_files["missing"]),
        next_actions=("uv build --all-packages",),
        data={
            "release_files": release_files,
            "gitlab": {
                "ci": ".gitlab-ci.yml",
                "merge_request_template": ".gitlab/merge_request_templates/default.md",
                "issue_template": ".gitlab/issue_templates/task.md",
            },
        },
    )
    _emit(result, json_output)


@quality_app.command
def release_policy(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Validate release version, GitLab, protection, and attestation policy."""
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
        next_actions=("ethos self audit",),
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
        required_gaps=tuple(report["missing_metadata"]),
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


@self_app.command
def audit(
    *,
    mode: str = "deep",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Audit ETHOS against its own product ontology."""
    repo = _root(root)
    if mode not in {"shape", "deep"}:
        result = EthosResult(
            command="self audit",
            ok=False,
            state="invalid",
            required_gaps=(f"invalid_audit_mode:{mode}",),
            next_actions=("ethos self audit --mode shape", "ethos self audit --mode deep"),
            data={"mode": mode, "allowed_modes": ["shape", "deep"]},
        )
        _emit(result, json_output)
        return
    audit_payload = self_audit_module.self_audit(repo, openspec_mode=mode)
    result = EthosResult(
        command="self audit",
        ok=bool(audit_payload["ok"]),
        state="clean" if audit_payload["ok"] else "gapped",
        summary={"openspec_mode": mode},
        required_gaps=tuple(audit_payload["required_gaps"]),
        next_actions=("ethos self hypothesize",)
        if audit_payload["ok"]
        else ("ethos self audit --mode deep",),
        data=audit_payload,
    )
    _emit(result, json_output)


@self_app.command
def openspec(
    *,
    change: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Audit official OpenSpec self-governance state."""
    repo = _root(root)
    report = openspec_self_governance_report(repo, change=change)
    result = EthosResult(
        command="self openspec",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "gapped",
        summary={
            "change": report["change"],
            "schema_name": report["schema_name"],
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos self audit",),
        data=report,
    )
    _emit(result, json_output)


@self_app.command
def observe(*, json_output: JsonFlag = False) -> None:
    """Observe ETHOS product shape."""
    result = EthosResult(
        command="self observe",
        ok=True,
        state="observed",
        summary={"observed": ["command-plane", "package-ontology", "docs", "schemas"]},
        next_actions=("ethos self hypothesize",),
    )
    _emit(result, json_output)


@self_app.command
def hypothesize(*, json_output: JsonFlag = False) -> None:
    """Record the next self-evolution hypothesis shape."""
    report = evolution_report(Path.cwd())
    result = EthosResult(
        command="self hypothesize",
        ok=bool(report["ok"]),
        state="ready" if report["ok"] else "gapped",
        summary={
            "loop": "observe -> hypothesize -> experiment -> prove -> canonize -> retire",
            "active_count": report["active_count"],
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos self experiment",),
        data=report,
    )
    _emit(result, json_output)


@self_app.command
def candidates(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Derive self-evolution candidates from current audit signals."""
    repo = _root(root)
    report = evolution_candidates(repo)
    result = EthosResult(
        command="self candidates",
        ok=bool(report["ok"]),
        state="ready",
        summary={"candidate_count": len(report["candidates"])},
        next_actions=("ethos campaign hypotheses",),
        data=report,
    )
    _emit(result, json_output)


@self_app.command
def experiment(*, json_output: JsonFlag = False) -> None:
    """Describe a self-evolution experiment."""
    result = EthosResult(
        command="self experiment",
        ok=True,
        state="ready",
        summary={"experiment": "run self audit and focused proof"},
        next_actions=("ethos self prove",),
    )
    _emit(result, json_output)


@self_app.command(name="prove")
def prove_self(
    *,
    mode: str = "deep",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Prove the active self-evolution hypothesis."""
    repo = _root(root)
    if mode not in {"shape", "deep"}:
        result = EthosResult(
            command="self prove",
            ok=False,
            state="invalid",
            required_gaps=(f"invalid_audit_mode:{mode}",),
            next_actions=("ethos self prove --mode shape", "ethos self prove --mode deep"),
            data={"mode": mode, "allowed_modes": ["shape", "deep"]},
        )
        _emit(result, json_output)
        return
    audit_payload = self_audit_module.self_audit(repo, openspec_mode=mode)
    ok = bool(audit_payload["ok"])
    result = EthosResult(
        command="self prove",
        ok=ok,
        state="proven" if ok else "gapped",
        summary={"proof": "self-audit", "openspec_mode": mode},
        required_gaps=tuple(audit_payload["required_gaps"]),
        next_actions=("ethos self canonize",) if ok else ("ethos self audit --mode deep",),
        data={"self_audit": audit_payload},
    )
    _emit(result, json_output)


@self_app.command(name="canonize")
def canonize_self(*, json_output: JsonFlag = False) -> None:
    """Canonize a proven self-evolution result."""
    result = EthosResult(
        command="self canonize",
        ok=True,
        state="ready",
        summary={"canonization": "write decision, schema, docs, and tests"},
        next_actions=("ethos self retire",),
    )
    _emit(result, json_output)


@self_app.command
def retire(*, json_output: JsonFlag = False) -> None:
    """Retire obsolete product residue."""
    result = EthosResult(
        command="self retire",
        ok=True,
        state="ready",
        summary={"retirement": "archive or delete obsolete projections"},
        next_actions=("ethos self audit",),
    )
    _emit(result, json_output)


@campaign_app.command(name="status")
def campaign_status(*, json_output: JsonFlag = False) -> None:
    """Report canonical campaign model."""
    report = evolution_report(Path.cwd())
    result = EthosResult(
        command="campaign status",
        ok=bool(report["ok"]),
        state="active",
        summary={"campaign": "ethos-product-maturation"},
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos self audit",),
        data=report,
    )
    _emit(result, json_output)


@campaign_app.command
def hypotheses(*, json_output: JsonFlag = False) -> None:
    """List active ETHOS self-evolution hypotheses."""
    ledger = evolution_ledger(Path.cwd())
    result = EthosResult(
        command="campaign hypotheses",
        ok=True,
        state="active",
        summary={"campaign": "ethos-product-maturation"},
        next_actions=("ethos self experiment",),
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


@intake_app.command(name="status")
def intake_status(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report adopter intake ledger readiness."""
    repo = _root(root)
    config_path = repo / ".ethos" / "intake.toml"
    gaps: tuple[str, ...] = ()
    provider = "unconfigured"
    configured = False
    if config_path.exists():
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            provider = "invalid"
            gaps = ("intake_config_invalid:.ethos/intake.toml",)
        else:
            configured_provider = str(config.get("provider") or "").strip()
            if configured_provider:
                provider = configured_provider
                configured = True
            else:
                provider = "invalid"
                gaps = ("intake_provider_missing:.ethos/intake.toml",)
    data = {
        "truth_boundary": "adopter-ledger",
        "provider": provider,
        "configured": configured,
        "expected_config": ".ethos/intake.toml",
        "adapters": ["backlog", "github", "gitlab"],
    }
    result = EthosResult(
        command="intake status",
        ok=not gaps,
        state="configured" if configured else ("invalid" if gaps else "unconfigured"),
        summary={
            "provider": data["provider"],
            "truth_boundary": data["truth_boundary"],
        },
        required_gaps=gaps,
        next_actions=("ethos adopt --dry-run",) if not configured else ("ethos plan --changed",),
        data=data,
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
        ok=contract["truth"] == "ethos-kernel-and-repository",
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
def assistants_context(*, json_output: JsonFlag = False) -> None:
    """Emit the ETHOS agentic context bundle."""
    bundle = context_bundle()
    result = EthosResult(
        command="assistants context",
        ok=True,
        state="ready",
        summary={"protocol_count": len(bundle["protocols"])},
        data={"context": bundle},
    )
    _emit(result, json_output)


@playbooks_app.command(name="check")
def playbooks_check(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check repo-local ETHOS playbook projection."""
    repo = _root(root)
    report = playbooks_report(repo)
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
    json_output: JsonFlag = False,
) -> None:
    """Route a subject to repo-local ETHOS playbooks."""
    repo = _root(root)
    route_subject = "changed-scope" if changed else subject
    report = route_playbook(repo, route_subject, require_explicit_subject=changed)
    result = EthosResult(
        command="playbooks route",
        ok=bool(report["ok"]),
        state="routed" if report["ok"] else "gapped",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    _emit(result, json_output)


@fleet_app.command(name="inspect")
def fleet_inspect(
    *,
    target: Path,
    json_output: JsonFlag = False,
) -> None:
    """Inspect an external repository as an ETHOS adopter."""
    report = inspect_adopter(target)
    result = EthosResult(
        command="fleet inspect",
        ok=bool(report["ok"]),
        state="ready" if report["ok"] else "gapped",
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
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report remaining product/adopter parity gaps."""
    repo = _root(root)
    report = parity_gaps_report(adopter=adopter, root=repo)
    result = EthosResult(
        command="parity gaps",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "gapped",
        summary={"adopter": report["adopter"], "gap_count": len(report["required_gaps"])},
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos parity shadow --target <repo>",),
        data=report,
    )
    _emit(result, json_output)


@parity_app.command(name="shadow")
def parity_shadow(
    *,
    target: Path,
    execute: bool = False,
    timeout_seconds: int = 30,
    json_output: JsonFlag = False,
) -> None:
    """Plan an external shadow parity comparison for an adopter."""
    if execute:
        from ethos_adapters.shadow import run_shadow_parity

        report = run_shadow_parity(target=target, timeout_seconds=timeout_seconds)
    else:
        report = shadow_parity_report(target=target)
    result = EthosResult(
        command="parity shadow",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos prove --full",),
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
    playbooks = playbooks_report(repo)
    adoption_scaffold = adoption_scaffold_report()
    parity_ledger = parity_ledger_report()
    parity_gaps = parity_gaps_report(root=repo)
    if audit.get("mode") == "adopter":
        scores = {
            "adopter_governance": int(bool(audit["ok"])),
            "schemas": int(bool(audit["schemas"]["ok"])),
            "claims": int(bool(audit["adopter"]["adopter"]["governance"]["claims"])),
            "docs": int(bool(audit["adopter"]["adopter"]["governance"]["docs"])),
            "assistant_projection": int(projection["truth"] == "ethos-kernel-and-repository"),
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
            "assistant_projection": int(projection["truth"] == "ethos-kernel-and-repository"),
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
    if audit.get("mode") != "adopter":
        result_required_gaps = result_required_gaps + tuple(claim_report["required_gaps"])
    gap_layers = {
        "product_self_audit": {
            "scope": "product_self_audit",
            "blocking": True,
            "ok": not result_required_gaps,
            "required_gaps": list(result_required_gaps),
            "gap_count": len(result_required_gaps),
        },
        "adopter_parity": {
            "scope": "global_capability_ledger",
            "blocking": False,
            "ok": bool(parity_gaps["ok"]),
            "required_gaps": list(parity_gaps["required_gaps"]),
            "gap_count": parity_pending_count,
        },
    }
    result = EthosResult(
        command="report",
        ok=ok,
        state="ready" if ok else "gapped",
        summary={
            "score": sum(scores.values()),
            "max_score": len(scores),
            "product_gap_count": len(result_required_gaps),
            "parity_pending_count": parity_pending_count,
        },
        required_gaps=result_required_gaps,
        next_actions=(
            ("ethos parity gaps --adopter <adopter>",)
            if parity_pending_count
            else ("ethos prove --full",)
        ),
        data={
            "scores": scores,
            "self_audit": audit,
            "docs": docs_report,
            "claims": claim_report,
            "assistant_projection": projection,
            "schema_validation": schemas_report,
            "evolution": evolution,
            "signature_policy": signature,
            "playbooks": playbooks,
            "adoption_scaffold": adoption_scaffold,
            "gap_layers": gap_layers,
            "parity": {
                "ledger": parity_ledger,
                "gaps": parity_gaps,
            },
            "profiles": list(available_profiles()),
        },
    )
    _emit(result, json_output)


@app.command
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


@app.command
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


def _self_audit_after_admission(repo: Path, decision: MutationDecision) -> dict[str, object]:
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
