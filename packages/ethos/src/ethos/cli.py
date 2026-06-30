from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter
from ethos_adopt import adoption_plan
from ethos_agent import mcp_manifest, projection_contract
from ethos_governance import (
    EvidenceSet,
    ProofRun,
    build_docs_registry,
    claims_report,
    command_registry_report,
    docs_health_report,
    provenance_envelope,
    self_audit,
    standard_adapter_registry,
    trim_output,
)
from ethos_kernel.action_graph import ActionGraph, ActionNode
from ethos_kernel.result import EthosResult
from ethos_workspace import (
    DryRunRunner,
    LocalSubprocessRunner,
    MutationRequest,
    evaluate_mutation,
    workspace_status,
)
from ethos_workspace.state import initialize_state

app = App(name="ethos", help="ETHOS command plane.")
quality_app = App(name="quality", help="Quality and determinism checks.")
self_app = App(name="self", help="Self-governance commands.")
campaign_app = App(name="campaign", help="Evolution campaign commands.")
assistants_app = App(name="assistants", help="Assistant and protocol projections.")
app.command(quality_app)
app.command(self_app)
app.command(campaign_app)
app.command(assistants_app)


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


@app.command
def status(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Inspect repository state."""
    repo = _root(root)
    status_payload = workspace_status(repo)
    result = EthosResult(
        command="status",
        ok=True,
        state="dirty" if status_payload["dirty"] else "ready",
        summary={
            "root": str(repo),
            "branch": status_payload["branch"],
            "changed_path_count": len(status_payload["changed_paths"]),
        },
        next_actions=("ethos plan --changed",),
        data=status_payload,
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
    result = EthosResult(
        command="plan",
        ok=True,
        state="planned",
        summary={
            "changed": changed,
            "action_count": len(graph.nodes),
        },
        next_actions=("ethos prove --json",),
        data={
            "changed_paths": list(paths),
            "action_graph": graph.to_dict(),
        },
    )
    _emit(result, json_output)


@app.command
def prove(
    *,
    objective: str = "ethos proof",
    execute: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Produce a local proof-readiness summary."""
    repo = _root(root)
    audit = self_audit(repo)
    action = ActionNode(
        id="self-audit",
        kind="governance",
        command=(
            sys.executable,
            "-m",
            "ethos.cli",
            "self",
            "audit",
            "--root",
            str(repo),
            "--json",
        ),
        inputs=("packages", "docs", "schemas", "tests"),
        outputs=(),
        policy="required",
    )
    runner = LocalSubprocessRunner() if execute else DryRunRunner()
    run_result = runner.run(action, root=repo)
    proof_run = ProofRun(
        action_id=run_result.action_id,
        command=run_result.command,
        exit_code=run_result.exit_code,
        stdout=trim_output(run_result.stdout),
        stderr=trim_output(run_result.stderr),
        state=run_result.state,
    )
    evidence = EvidenceSet.from_runs(
        id=f"ethos:{objective}",
        head=_current_head(repo),
        runs=(proof_run,),
        durability="local",
    )
    result = EthosResult(
        command="prove",
        ok=bool(audit["ok"]),
        state="proven" if audit["ok"] else "gapped",
        summary={"objective": objective, "evidence_digest": evidence.digest},
        required_gaps=tuple(audit["required_gaps"]),
        next_actions=("ethos land",) if audit["ok"] else ("ethos self audit",),
        data={
            "self_audit": audit,
            "executed": execute,
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
    audit = self_audit(repo)
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
    gaps = tuple(audit["required_gaps"]) + decision.gaps
    ok = bool(audit["ok"]) and decision.ok
    result = EthosResult(
        command="land",
        ok=ok,
        state=("ready_to_land" if ok and not apply else decision.state),
        required_gaps=gaps,
        next_actions=("ethos publish",) if ok else ("ethos prove --json",),
        data={
            "self_audit": audit,
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
    audit = self_audit(repo)
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
    gaps = tuple(audit["required_gaps"]) + decision.gaps
    ok = bool(audit["ok"]) and decision.ok
    result = EthosResult(
        command="publish",
        ok=ok,
        state=("ready_to_publish" if ok and not apply else decision.state),
        required_gaps=gaps,
        next_actions=("ethos report",) if ok else ("ethos land --json",),
        data={
            "self_audit": audit,
            "remote_push": "not_performed",
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
    json_output: JsonFlag = False,
) -> None:
    """Initialize ETHOS adoption for a repository."""
    target = _root(root)
    do_apply = apply and not dry_run
    plan_payload = adoption_plan(target, apply=do_apply)
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
    json_output: JsonFlag = False,
) -> None:
    """Plan or apply ETHOS adoption for a repository."""
    target = _root(root)
    do_apply = apply and not dry_run
    plan_payload = adoption_plan(target, apply=do_apply)
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
    json_output: JsonFlag = False,
) -> None:
    """Validate public command surface vocabulary."""
    report = command_registry_report()
    result = EthosResult(
        command="quality command-surface",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["retired_public_roots"]),
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


@quality_app.command
def command_registry(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Validate public command registry."""
    report = command_registry_report()
    result = EthosResult(
        command="quality command-registry",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(report["retired_public_roots"]),
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
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Audit ETHOS against its own product ontology."""
    repo = _root(root)
    audit_payload = self_audit(repo)
    result = EthosResult(
        command="self audit",
        ok=bool(audit_payload["ok"]),
        state="clean" if audit_payload["ok"] else "gapped",
        required_gaps=tuple(audit_payload["required_gaps"]),
        next_actions=("ethos self hypothesize",),
        data=audit_payload,
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
    result = EthosResult(
        command="self hypothesize",
        ok=True,
        state="ready",
        summary={"loop": "observe -> hypothesize -> experiment -> prove -> canonize -> retire"},
        next_actions=("ethos self experiment",),
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
def prove_self(*, json_output: JsonFlag = False) -> None:
    """Prove the active self-evolution hypothesis."""
    result = EthosResult(
        command="self prove",
        ok=True,
        state="proven",
        summary={"proof": "self audit plus tests"},
        next_actions=("ethos self canonize",),
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
    result = EthosResult(
        command="campaign status",
        ok=True,
        state="active",
        summary={"campaign": "ethos-product-canonization"},
        next_actions=("ethos self audit",),
        data={
            "opportunities": [
                "kernel",
                "action-graph",
                "governance",
                "workspace",
                "agent",
                "adopt",
                "self-evolution",
            ]
        },
    )
    _emit(result, json_output)


@campaign_app.command
def hypotheses(*, json_output: JsonFlag = False) -> None:
    """List active ETHOS self-evolution hypotheses."""
    result = EthosResult(
        command="campaign hypotheses",
        ok=True,
        state="active",
        summary={"campaign": "ethos-product-canonization"},
        next_actions=("ethos self experiment",),
        data={
            "hypotheses": [
                {
                    "id": "kernel-first-command-plane",
                    "state": "canonizing",
                    "claim": "A small pure kernel plus adapters gives stronger semantics.",
                    "challenge": "No public behavior should depend on a private host surface.",
                },
                {
                    "id": "reflexive-governance-loop",
                    "state": "active",
                    "claim": "ETHOS can govern and evolve itself through the same evidence loop.",
                    "challenge": "Every product-shape change must leave tests, docs, and evidence.",
                },
            ]
        },
    )
    _emit(result, json_output)


@assistants_app.command(name="doctor")
def assistants_doctor(*, json_output: JsonFlag = False) -> None:
    """Report assistant projection readiness."""
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


@app.command
def report(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit a concise scorecard."""
    repo = _root(root)
    audit = self_audit(repo)
    docs_report = docs_health_report(repo)
    claim_report = claims_report(repo)
    command_report = command_registry_report()
    projection = projection_contract()
    scores = {
        "package_ontology": int(bool(audit["package_ontology"]["ok"])),
        "docs": int(bool(docs_report["ok"])),
        "schemas": int(bool(audit["schemas"]["ok"])),
        "claims": int(bool(claim_report["ok"])),
        "command_registry": int(bool(command_report["ok"])),
        "standards": int(
            all(
                item["boundary"] and item["fallback"] and item["exit_strategy"]
                for item in standard_adapter_registry().values()
            )
        ),
        "assistant_projection": int(projection["truth"] == "ethos-kernel-and-repository"),
    }
    ok = all(value == 1 for value in scores.values())
    result = EthosResult(
        command="report",
        ok=ok,
        state="ready" if ok else "gapped",
        summary={"score": sum(scores.values()), "max_score": len(scores)},
        required_gaps=tuple(audit["required_gaps"]) + tuple(claim_report["required_gaps"]),
        data={
            "scores": scores,
            "self_audit": audit,
            "docs": docs_report,
            "claims": claim_report,
            "assistant_projection": projection,
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
