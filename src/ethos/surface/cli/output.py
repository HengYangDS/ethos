"""CLI result rendering and exit-status enforcement."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated
from typing import TextIO

from cyclopts import Parameter

from ethos.adapters.repo.git import git_common_dir
from ethos.domain.execution import process_failure_result
from ethos.domain.execution import profile_failure_result
from ethos.result import EthosResult
from ethos.result import apply_payload_budget

if TYPE_CHECKING:
    from ethos.adapters.process import ProcessExecutionError

JsonFlag = Annotated[bool, Parameter(name="--json")]


def emit(
    result: EthosResult,
    *,
    json_output: bool,
    enforce: bool = True,
    artifact_root: Path | None = None,
) -> None:
    """Render CLI results without writing diagnostics into an MCP protocol stream."""
    if json_output and artifact_root is not None:
        common_dir = git_common_dir(artifact_root)
        receipt_root = Path(common_dir) / "ethos" if common_dir else artifact_root / ".ethos"
        result = apply_payload_budget(result, root=receipt_root)
    stream = sys.stderr if result.command == "mcp" else sys.stdout
    if json_output:
        frame = f"{result.to_json()}\n"
    else:
        lines = [f"{result.command}: {result.state}"]
        lines.extend(f"why: {reason}" for reason in _human_reasons(result))
        if result.user_decision_required:
            lines.append("decision: human choice required")
        if result.next_action:
            lines.append(f"next: {result.next_action}")
        frame = "\n".join(lines) + "\n"
    _write_frame(stream, frame)
    native_failure = result.data.get("error_boundary") in {"git_execution", "process_execution"}
    if (enforce or native_failure) and result.verdict != "pass":
        raise SystemExit(1)


def _write_frame(stream: TextIO, frame: str) -> None:
    """Deliver one complete result frame or fail without changing its verdict."""
    delivery_gap = ""
    try:
        if stream.write(frame) != len(frame):
            delivery_gap = "output_partial"
        else:
            stream.flush()
    except BrokenPipeError:
        delivery_gap = "output_closed"
    except BlockingIOError:
        delivery_gap = "output_backpressure"
    except (OSError, ValueError):
        delivery_gap = "output_unavailable"
    if delivery_gap:
        try:
            with Path(os.devnull).open("w") as sink:
                os.dup2(sink.fileno(), stream.fileno())
        except (AttributeError, OSError, ValueError):
            pass
        if stream is not sys.stderr:
            try:
                sys.stderr.write(f"ethos: {delivery_gap}\n")
                sys.stderr.flush()
            except (OSError, ValueError):
                pass
        raise SystemExit(1)


def _human_reasons(result: EthosResult) -> tuple[str, ...]:
    """Prefer owner-supplied diagnostics and expose every distinct blocker."""
    adverse = [
        item
        for item in result.diagnostics
        if str(item.get("severity") or "").lower() in {"warning", "error"}
    ]
    reasons: list[str] = []
    rendered_codes: set[str] = set()
    for gap in dict.fromkeys(result.required_gaps):
        code = gap.partition(":")[0]
        messages = [
            str(item["message"])
            for item in adverse
            if item.get("code") == code and item.get("message")
        ]
        reasons.extend(messages or [_human_gap(gap)])
        rendered_codes.add(code)
    for item in adverse:
        code = str(item.get("code") or "")
        if code not in rendered_codes:
            reasons.append(str(item.get("message") or _human_gap(code) or item["severity"]))
    return tuple(dict.fromkeys(reasons))


def _human_gap(gap: str) -> str:
    """Space a stable reason code without redefining its meaning."""
    code, separator, detail = gap.partition(":")
    label = code.replace("_", " ")
    return f"{label}: {detail}" if separator else label


def emit_invalid_repository_profile(*, command: str, json_output: bool, enforce: bool) -> None:
    """Render the shared invalid-profile result with the requested CLI enforcement."""
    emit(profile_failure_result(command), json_output=json_output, enforce=enforce)


def emit_process_execution_failure(
    *, command: str, error: ProcessExecutionError, json_output: bool, root: Path | None = None
) -> None:
    """Render the shared application failure without reinterpreting its meaning."""
    emit(
        process_failure_result(command, error, root=root),
        json_output=json_output,
        enforce=True,
    )
