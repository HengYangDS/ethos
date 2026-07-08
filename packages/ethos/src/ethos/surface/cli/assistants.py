"""Assistants command group — MCP, context projection/index, playbook doctor, search.

Surface module: binds args, calls assistant/context adapters, emits. Registers onto
the shared assistants_app from _base; cli.py imports this module so the decorators
run. Imports only what this group needs (the heavy context/mcp deps load only when
this group is imported).
"""

from __future__ import annotations

from ethos.adapters.store.retrieval.indexing import purge_context_index
from ethos.adapters.store.retrieval.indexing import rebuild_context_index
from ethos.adapters.store.retrieval.query import context_eval_report
from ethos.adapters.store.retrieval.query import search_context_index
from ethos.assistants.context.bundle import context_bundle
from ethos.assistants.mcp import mcp_manifest
from ethos.assistants.projections import projection_contract
from ethos.assistants.server import mcp_server_descriptor
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import assistants_app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.context_projection import ASSISTANT_TRUTH_BOUNDARY
from ethos_core.contracts.context_projection import context_retrieval_smoke_queries
from ethos_core.result import EthosResult


@assistants_app.command(name="doctor")
def assistants_doctor(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report assistant projection readiness."""
    resolve_root(root)
    contract = projection_contract()
    result = EthosResult(
        command="assistants doctor",
        ok=True,
        state="ready",
        summary={"surface_count": len(contract["surfaces"])},
        next_actions=("ethos assistants mcp-manifest",),
        data={"contract": contract},
    )
    emit(result, json_output=json_output, enforce=False)


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
    emit(result, json_output=json_output, enforce=False)


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
    emit(result, json_output=json_output, enforce=False)


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
    emit(result, json_output=json_output, enforce=False)


@assistants_app.command(name="context")
def assistants_context(
    *,
    root: RootOption | None = None,
    scope: str = "repo",
    query: str | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit the ETHOS agentic context bundle."""
    repo = resolve_root(root)
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
    emit(result, json_output=json_output, enforce=False)


@assistants_app.command(name="search")
def assistants_search(
    query: str,
    *,
    root: RootOption | None = None,
    limit: int = 10,
    json_output: JsonFlag = False,
) -> None:
    """Search the local source-verified context projection."""
    repo = resolve_root(root)
    report = search_context_index(repo, query, limit=limit)
    result = EthosResult(
        command="assistants search",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=dict(report["summary"]),
        required_gaps=tuple(report["required_gaps"]),
        data={"selection": report["selection"]},
    )
    emit(result, json_output=json_output, enforce=False)


@assistants_app.command(name="context-index")
def assistants_context_index(
    *,
    root: RootOption | None = None,
    apply: bool = False,
    authorize: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Build the local context projection index."""
    repo = resolve_root(root)
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
    emit(result, json_output=json_output, enforce=False)


@assistants_app.command(name="context-purge")
def assistants_context_purge(
    *,
    root: RootOption | None = None,
    apply: bool = False,
    authorize: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Purge the local context projection index."""
    repo = resolve_root(root)
    report = purge_context_index(repo, apply=apply, authorized=authorize)
    result = EthosResult(
        command="assistants context-purge",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=dict(report["summary"]),
        required_gaps=tuple(report["required_gaps"]),
        data=dict(report.get("data", {})),
    )
    emit(result, json_output=json_output, enforce=False)


@assistants_app.command(name="context-eval")
def assistants_context_eval(
    *,
    root: RootOption | None = None,
    suite: str = "smoke",
    json_output: JsonFlag = False,
) -> None:
    """Evaluate the local context projection index."""
    repo = resolve_root(root)
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
    emit(result, json_output=json_output, enforce=False)
