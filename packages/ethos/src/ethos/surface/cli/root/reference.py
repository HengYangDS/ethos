"""Root reference and governance inspection commands."""

from __future__ import annotations

from pathlib import Path

import ethos.domain.status as status_domain
from ethos.adapters.openspec.core import openspec_governance_report
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult
from ethos_core.state.invalid import UNCLASSIFIED
from ethos_core.state.invalid import explain_gap


@app.command(show=False)
def explain(gap_or_signal: str, *, json_output: JsonFlag = False) -> None:
    """Explain a governance gap or advisory signal as a read-only invalid-state projection."""
    data = explain_gap(gap_or_signal)
    category_id = str(data["invalid_state"]["id"])
    result = EthosResult(
        command="explain",
        ok=category_id != UNCLASSIFIED,
        state="explained" if category_id != UNCLASSIFIED else "unclassified",
        summary={"gap": gap_or_signal, "invalid_state": category_id},
        required_gaps=(
            () if category_id != UNCLASSIFIED else (f"unclassified_invalid_state:{gap_or_signal}",)
        ),
        data=data,
    )
    emit(result, json_output=json_output, enforce=False)


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
    emit(result, json_output=json_output, enforce=False)


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
        emit(result, json_output=json_output, enforce=False)
        return
    audit_payload = status_domain.audit_for_root(repo, openspec_mode=mode)
    result = EthosResult(
        command="audit",
        ok=bool(audit_payload["ok"]),
        state="clean" if audit_payload["ok"] else "gapped",
        summary={"openspec_mode": mode},
        required_gaps=tuple(audit_payload["required_gaps"]),
        next_actions=("ethos report",) if audit_payload["ok"] else ("ethos audit --mode deep",),
        data=audit_payload,
    )
    emit(result, json_output=json_output, enforce=False)


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
    emit(result, json_output=json_output, enforce=False)
