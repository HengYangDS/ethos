"""Bind an admitted native producer's fresh reports without executing replacement checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.gates.go as native_go
from ethos.adapters.repo.git import git_files

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.gates import Gate


def preflight(root: Path, gate: Gate, languages: set[str], axis: str) -> None:
    """Require standard report IO and explicit producer inputs before its effect."""
    required = {
        "go": {"go-test-json", "go-coverage"},
        "javascript": {"junit", "lcov"},
    }
    expected = (
        {"sarif"}
        if axis == "static-analysis"
        else set().union(
            *(required.get(language, {f"unsupported:{language}"}) for language in languages)
        )
    )
    declared = {source.format for source in gate.native_reports}
    if declared != expected:
        message = "native_report_contract_incomplete:" + ",".join(sorted(expected - declared))
        raise ValueError(message)
    if axis != "behavior" or languages != {"go"}:
        message = "native_report_producer_unavailable"
        raise ValueError(message)
    native_go.preflight(root, gate.command, reports=tuple(gate.native_reports))
    tracked = set(git_files(root))
    if any(
        path not in tracked or (root / path).is_symlink() or not (root / path).is_file()
        for path in gate.source_inputs
    ):
        message = "native_report_source_input_unavailable"
        raise ValueError(message)
    for source in gate.native_reports:
        if source.channel == "file" and not any(
            argument.endswith("{reports}/" + str(source.path)) for argument in gate.command
        ):
            message = "native_report_output_unbound:" + str(source.path)
            raise ValueError(message)
