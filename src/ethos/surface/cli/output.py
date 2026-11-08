"""CLI result rendering and exit-status enforcement.

A result exits 0 or, when its verdict is enforced and does not pass, 1; a usage refusal exits 2
and a result that cannot be delivered exits 3.
"""

from __future__ import annotations

import os
import sys
from contextlib import suppress
from pathlib import Path
from typing import Annotated
from typing import TextIO

from cyclopts import Parameter

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import git_common_dir
from ethos.application.invocation import process_failure_result
from ethos.application.invocation import profile_failure_result
from ethos.result import EthosResult
from ethos.result import apply_payload_budget
from ethos.surface.cli.root_binding import resolved_root
from ethos.surface.runtime_identity import with_runtime

JsonFlag = Annotated[bool, Parameter(name="--json")]


def emit(
    result: EthosResult,
    *,
    json_output: bool,
    enforce: bool = True,
    artifact_root: Path | None = None,
) -> None:
    """Render CLI results without writing diagnostics into an MCP protocol stream."""
    if json_output:
        # Every command's result is bounded. The store is resolved only when detail is written, so
        # a small result, including the report of a failed process, never spawns one.
        result = apply_payload_budget(
            with_runtime(result), root=lambda: _detail_store(artifact_root)
        )
    # A usage refusal is an error: its human frame goes to stderr, beside any JSON on stdout.
    usage = result.state == "usage_refused"
    stream = sys.stderr if result.command == "mcp" or (usage and not json_output) else sys.stdout
    _write_frame(stream, f"{result.to_json()}\n" if json_output else _human_frame(result))
    if usage:
        if json_output:
            # The JSON on stdout is the result; this copy for a person is best effort.
            with suppress(OSError, ValueError):
                sys.stderr.write(_human_frame(result))
                sys.stderr.flush()
        raise SystemExit(2)
    native_failure = result.data.get("error_boundary") in {"git_execution", "process_execution"}
    if (enforce or native_failure) and result.verdict != "pass":
        raise SystemExit(1)


def _human_frame(result: EthosResult) -> str:
    """Render one result for a person: its state, every distinct reason and the next action."""
    lines = [f"{result.command}: {result.state}"]
    lines.extend(f"why: {reason}" for reason in _human_reasons(result))
    if result.user_decision_required:
        lines.append("decision: human choice required")
    if result.next_action:
        lines.append(f"next: {result.next_action}")
    return "\n".join(lines) + "\n"


def _detail_store(artifact_root: Path | None) -> Path:
    """Return the ETHOS store of the repository the command resolved, for its detail cache."""
    anchor = artifact_root or resolved_root() or Path.cwd()
    try:
        common_dir = git_common_dir(anchor)
    except ProcessExecutionError as error:
        # The bound treats an unresolvable store like an unwritable one: the result stays inline.
        raise OSError(error.code) from error
    return Path(common_dir) / "ethos" if common_dir else anchor / ".ethos"


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
            with Path(os.devnull).open("w", encoding="utf-8") as sink:
                os.dup2(sink.fileno(), stream.fileno())
        except (AttributeError, OSError, ValueError):
            pass
        if stream is not sys.stderr:
            try:
                sys.stderr.write(f"ethos: {delivery_gap}\n")
                sys.stderr.flush()
            except (OSError, ValueError):
                pass
        # An undelivered result is not the command's verdict; it exits apart from every verdict.
        raise SystemExit(3)


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


def emit_invalid_repository_profile(
    *, command: str, json_output: bool, enforce: bool, root: Path | None = None
) -> None:
    """Render the shared invalid-profile result with the requested CLI enforcement."""
    emit(profile_failure_result(command, root), json_output=json_output, enforce=enforce)


def emit_process_execution_failure(
    *, command: str, error: ProcessExecutionError, json_output: bool, root: Path | None = None
) -> None:
    """Render the shared application failure without reinterpreting its meaning."""
    emit(
        process_failure_result(command, error, root=root),
        json_output=json_output,
        enforce=True,
    )
