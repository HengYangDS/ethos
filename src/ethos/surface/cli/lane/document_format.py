"""Project native document formatting through the existing Work Lane boundary."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.gates.markdown import observe_working_documents
from ethos.adapters.mutation.document_format import format_documents
from ethos.surface.cli.lane.lifecycle import AppliedLaneCommandOptions
from ethos.surface.cli.lane.lifecycle import lane_app
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.root_binding import resolve_root


class _FormatDocuments(AppliedLaneCommandOptions):
    command = "lane format-documents"
    preview_patch: Annotated[str | None, Parameter(name="--preview-patch")] = None


_DEFAULT_OPTIONS = _FormatDocuments()


@lane_app.command(name="format-documents")
def lane_format_documents(
    options: Annotated[_FormatDocuments, Parameter(name="*")] = _DEFAULT_OPTIONS,
) -> None:
    """Preview native Prettier output or apply its exact admitted patch."""
    report: dict[str, object]
    try:
        repo = resolve_root(options.root)
        report = format_documents(
            root=repo,
            sources=observe_working_documents(repo),
            apply=options.apply,
            preview_patch=(
                Path(options.preview_patch).read_bytes().decode("utf-8")
                if options.preview_patch is not None
                else None
            ),
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report = {
            "verdict": "block",
            "state": "blocked",
            "applied": False,
            "required_gaps": ["document_format_inputs_unavailable"],
            "failure": {"type": type(error).__name__, "message": str(error)},
            "next_action": "Reobserve the exact authoring inputs and obtain a fresh preview.",
        }
    project_lane_result(options.command, report, enforce=True, json_output=options.json_output)
