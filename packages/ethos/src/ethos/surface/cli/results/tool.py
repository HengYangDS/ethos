from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TypedDict
from typing import Unpack
from typing import cast

from ethos.adapters.gates.tool import quality_tool_report
from ethos.surface.cli._base import emit
from ethos_core.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


class QualityToolResultKwargs(TypedDict):
    """Keyword inputs for emitting a quality-tool CLI result."""

    root: Path
    gate_id: str
    tool: str
    command: Sequence[str]
    files: Sequence[str]
    result_command: str
    json_output: bool


def emit_quality_tool_result(**kwargs: Unpack[QualityToolResultKwargs]) -> None:
    """Run a quality-tool adapter report and emit its CLI result."""
    report = quality_tool_report(
        root=kwargs["root"],
        gate_id=kwargs["gate_id"],
        tool=kwargs["tool"],
        command=list(kwargs["command"]),
        files=list(kwargs["files"]),
    )
    result = EthosResult(
        command=kwargs["result_command"],
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=kwargs["json_output"], enforce=False)
