"""Connect native document formatting to the existing exact carrier effect owner."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.gates.markdown import native_document_observation
from ethos.adapters.gates.tool import quality_source_files
from ethos.adapters.mutation.carrier_edit import apply_carrier_edits
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_effect_outcome
from ethos.adapters.repo.content.observation import read_regular_bytes
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.repair import CarrierEdit

if TYPE_CHECKING:
    from pathlib import Path


def format_documents(
    *,
    root: Path,
    sources: dict[str, str],
    apply: bool = False,
    preview_patch: str | None = None,
) -> dict[str, object]:
    """Preview original Prettier output or apply its unchanged exact preview.

    The working selection owner supplies canonical current text. The caller
    retains these preimages until acceptance or recovery. OpenSpec and immutable
    records remain observable inputs but never enter this formatter's write set.
    Native format checks remain separate, nonmutating observations.
    """
    repo = root.resolve()
    texts = dict(sources)
    report: dict[str, object] = {
        "verdict": "pass",
        "state": "planned",
        "applied": False,
        "input_kind": "working-tree",
        "checked_paths": sorted(texts),
        "format_paths": [],
        "excluded_paths": [],
        "patch": "",
        "edits": [],
        "required_gaps": [],
        "next_action": "",
        "user_decision_required": False,
    }
    try:
        if any(not path.endswith(".md") for path in texts):
            return _refused(report, ["document_format_input_not_markdown"])
        protected = (*load_repository_paradigm().immutable_roots, "openspec/")
        format_paths = tuple(path for path in sorted(texts) if not path.startswith(protected))
        report.update(
            format_paths=list(format_paths),
            excluded_paths=sorted(set(texts) - set(format_paths)),
        )
        gaps = _source_gaps(repo, texts)
        if gaps:
            return _refused(report, gaps)
        observed = native_document_observation(
            repo,
            texts,
            lint=False,
            format_paths=format_paths,
            repository_paths=tuple(quality_source_files(repo)),
        )
        report["native_format"] = {
            "command": observed["command"],
            "diagnostics": observed["diagnostics"],
            "stderr": observed["stderr"],
        }
        gaps = _source_gaps(repo, texts)
        if gaps:
            return _refused(report, gaps)
        edits = tuple(
            CarrierEdit(path, texts[path], observed["formatted"][path])
            for path in format_paths
            if texts[path] != observed["formatted"][path]
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return {
            **_refused(report, ["document_format_observation_unavailable"]),
            "failure": {"type": type(error).__name__, "message": str(error)},
        }
    if apply and edits and preview_patch is None:
        return _refused(report, ["document_format_preview_required"])
    effect = apply_carrier_edits(
        root=repo,
        edits=edits,
        apply=apply,
        preview_patch=preview_patch,
        next_action="Apply this exact preview through the existing Work Lane formatter.",
    )
    return {**report, **effect}


def _source_gaps(root: Path, sources: dict[str, str]) -> list[str]:
    """Observe every supplied preimage, including unchanged and protected documents."""
    return [
        f"document_format_source_changed:{path}"
        for path, text in sources.items()
        if read_regular_bytes(
            root,
            path,
            unsafe_gap=f"source_member_link_or_type_forbidden:{path}",
            unstable_gap=f"source_member_changed:{path}",
            size_gap=f"source_member_size_exceeded:{path}",
        )
        != text.encode("utf-8")
    ]


def _refused(report: dict[str, object], gaps: list[str]) -> dict[str, object]:
    return {
        **report,
        "verdict": "block",
        "state": "blocked",
        "applied": False,
        "required_gaps": gaps,
        "next_action": "Reobserve the selected working documents and obtain a fresh preview.",
        "lifecycle_effect_outcome": lifecycle_effect_outcome(kind="zero_effect"),
    }
