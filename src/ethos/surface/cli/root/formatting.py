"""Expose literal native formatting with preview, check and exact admitted apply."""

from ethos.adapters.mutation.formatting import format_sources
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@app.command(name="format")
def format_command(
    paths: tuple[str, ...] = (),
    *,
    check: bool = False,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Preview formatting, check without mutation, or apply admitted literal sources."""
    repo = resolve_root(root)
    report = format_sources(root=repo, paths=paths, check=check, apply=apply)
    emit(
        EthosResult(
            command="format",
            verdict=report_verdict(report),
            state=str(report["state"]),
            required_gaps=tuple(string_sequence(report["required_gaps"])),
            next_action=str(report.get("next_action") or ""),
            data=report,
        ),
        json_output=json_output,
        artifact_root=repo,
    )
