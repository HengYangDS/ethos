"""Root reference and governance inspection commands."""

from __future__ import annotations

from pathlib import Path

import ethos.domain.status as status_domain
from ethos.adapters.openspec.archive.query import archive_query_report
from ethos.adapters.openspec.core import openspec_governance_report
from ethos.normalization.core import string_mapping
from ethos.normalization.core import string_sequence
from ethos.repository.registry.docs.health import docs_health_report
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.result import EthosResult
from ethos.state.invalid import UNCLASSIFIED
from ethos.state.invalid import explain_gap
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import load_command_groups
from ethos.surface.cli._base import resolve_root


def _live_cyclopts_command(tokens: list[str]) -> str:
    """Return an unknown command path using the loaded Cyclopts operation tree."""
    command_chain, apps, remaining = app.parse_commands(tokens)
    if not command_chain:
        return " ".join(("ethos", *(token for token in tokens if not token.startswith("-"))))
    if apps[-1].default_command is None and remaining and not remaining[0].startswith("-"):
        return " ".join(("ethos", *command_chain, remaining[0]))
    return ""


def docs_registry_report(root: Path) -> dict[str, object]:
    """Validate docs metadata and examples against the live command surface."""
    load_command_groups([])
    return docs_health_report(root, command_validator=_live_cyclopts_command)


@app.command(show=False)
def explain(gap_or_signal: str, *, json_output: JsonFlag = False) -> None:
    """Explain a governance gap or advisory signal as a read-only invalid-state projection."""
    data = string_mapping(explain_gap(gap_or_signal))
    category_id = str(string_mapping(data.get("invalid_state")).get("id") or "")
    result = EthosResult(
        command="explain",
        ok=True,
        state="explained" if category_id != UNCLASSIFIED else "unclassified",
        summary={"gap": gap_or_signal, "invalid_state": category_id},
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
        required_gaps=tuple(string_sequence(audit_payload.get("required_gaps"))),
        next_actions=("ethos status",) if audit_payload["ok"] else ("ethos audit --mode deep",),
        data=audit_payload,
    )
    emit(result, json_output=json_output, enforce=False)


@app.command(show=False)
def openspec(
    *,
    change: str | None = None,
    archive_id: str | None = None,
    lifecycle: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Audit official OpenSpec governance state."""
    repo = resolve_root(root)
    if change and archive_id:
        ok, state, summary, gaps, actions, data = (
            False,
            "invalid",
            {"change": change, "archive_id": archive_id, "lifecycle": lifecycle},
            ("openspec_change_archive_selector_conflict",),
            ("use either --change or --archive-id",),
            {},
        )
    elif archive_id:
        archive = archive_query_report(repo, logical_id=archive_id)
        ok, state, summary = (
            bool(archive["ok"]),
            str(archive["state"]),
            {"archive_id": archive_id, "lifecycle": False},
        )
        gaps, data = tuple(str(gap) for gap in archive["required_gaps"]), {"archive_query": archive}
        actions = ("use a logical Change ID, not a dated archive directory",) if not ok else ()
    else:
        report = openspec_governance_report(repo, change=change, lifecycle=lifecycle)
        ok, state, summary = (
            bool(report["ok"]),
            "clean" if report["ok"] else "gapped",
            {
                "change": report["change"],
                "schema_name": report["schema_name"],
                "lifecycle": lifecycle,
            },
        )
        gaps, actions, data = tuple(report["required_gaps"]), ("ethos audit",), report
    emit(
        EthosResult(
            command="openspec",
            ok=ok,
            state=state,
            summary=summary,
            required_gaps=gaps,
            next_actions=actions,
            data=data,
        ),
        json_output=json_output,
        enforce=False,
    )
