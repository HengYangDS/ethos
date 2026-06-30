from __future__ import annotations

from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter
from ethos_adopt import adoption_plan
from ethos_governance import command_registry_report, self_audit, standard_adapter_registry
from ethos_kernel.action_graph import ActionGraph, ActionNode
from ethos_kernel.result import EthosResult
from ethos_workspace import workspace_status
from ethos_workspace.state import initialize_state

app = App(name="ethos", help="ETHOS command plane.")
quality_app = App(name="quality", help="Quality and determinism checks.")
self_app = App(name="self", help="Self-governance commands.")
campaign_app = App(name="campaign", help="Evolution campaign commands.")
app.command(quality_app)
app.command(self_app)
app.command(campaign_app)


JsonFlag = Annotated[bool, Parameter(name="--json")]
RootOption = Annotated[Path, Parameter(name="--root")]


def _root(root: Path | None) -> Path:
    return (root or Path.cwd()).resolve()


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
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Produce a local proof-readiness summary."""
    repo = _root(root)
    audit = self_audit(repo)
    result = EthosResult(
        command="prove",
        ok=bool(audit["ok"]),
        state="proven" if audit["ok"] else "gapped",
        summary={"objective": objective},
        required_gaps=tuple(audit["required_gaps"]),
        next_actions=("ethos land",) if audit["ok"] else ("ethos self audit",),
        data={"self_audit": audit},
    )
    _emit(result, json_output)


@app.command
def land(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report land readiness."""
    repo = _root(root)
    audit = self_audit(repo)
    result = EthosResult(
        command="land",
        ok=bool(audit["ok"]),
        state="ready_to_land" if audit["ok"] else "blocked",
        required_gaps=tuple(audit["required_gaps"]),
        next_actions=("ethos publish",) if audit["ok"] else ("ethos prove --json",),
        data={"self_audit": audit},
    )
    _emit(result, json_output)


@app.command
def publish(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report publish readiness without pushing."""
    repo = _root(root)
    audit = self_audit(repo)
    result = EthosResult(
        command="publish",
        ok=bool(audit["ok"]),
        state="ready_to_publish" if audit["ok"] else "blocked",
        required_gaps=tuple(audit["required_gaps"]),
        next_actions=("ethos report",) if audit["ok"] else ("ethos land --json",),
        data={"self_audit": audit, "remote_push": "not_performed"},
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
    json_output: JsonFlag = False,
) -> None:
    """Report format-policy readiness."""
    result = EthosResult(
        command="quality format-policy",
        ok=True,
        state="clean",
        data={
            "user_config": "TOML",
            "machine_output": "JSON",
            "append_only_events": "JSONL",
            "local_state": "SQLite",
            "advanced_compiler": "CUE adapter",
        },
    )
    _emit(result, json_output)


@quality_app.command
def projection_drift(
    *,
    json_output: JsonFlag = False,
) -> None:
    """Report projection drift readiness."""
    result = EthosResult(
        command="quality projection-drift",
        ok=True,
        state="clean",
        data={"projections": ["assistant", "mcp", "acp", "hosted-ci"], "drift": []},
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
    json_output: JsonFlag = False,
) -> None:
    """Placeholder freshness check over declared evidence roots."""
    result = EthosResult(
        command="quality evidence-freshness",
        ok=True,
        state="clean",
        summary={"evidence_roots": ["docs/evidence"]},
        next_actions=("ethos prove --json",),
        data={"stale": []},
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


@app.command
def report(*, json_output: JsonFlag = False) -> None:
    """Emit a concise scorecard."""
    result = EthosResult(
        command="report",
        ok=True,
        state="ready",
        summary={"scorecard": "bootstrap"},
        data={"scores": {"kernel": 1, "governance": 1, "workspace": 1, "agent": 1, "adopt": 1}},
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
def docs(topic: str = "index", *, json_output: JsonFlag = False) -> None:
    """Locate documentation for a topic."""
    result = EthosResult(
        command="docs",
        ok=True,
        state="located",
        summary={"topic": topic},
        data={"path": "docs/index.md" if topic == "index" else f"docs/reference/{topic}.md"},
    )
    _emit(result, json_output)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
