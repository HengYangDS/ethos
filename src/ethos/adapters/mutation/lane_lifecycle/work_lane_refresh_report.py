"""The report of one Work Lane refresh, its continuation and the exact refresh request."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.process import ProcessExecutionError

if TYPE_CHECKING:
    from pathlib import Path


def refresh_report(
    context: tuple[str, str, str, str],
    head: str,
    state: str,
    gaps: list[str],
    **details: object,
) -> dict[str, object]:
    """Project one refresh outcome with the lane and candidate coordinates it judged."""
    branch, candidate_branch, candidate_head, candidate_path = context
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "branch": branch,
        "head": head,
        "required_gaps": gaps,
        "candidate_branch": candidate_branch,
        "candidate_head": candidate_head,
        "candidate_path": candidate_path,
        **details,
    }


def process_failure(error: Exception) -> dict[str, object]:
    """Keep native refusal evidence instead of reducing it to its code."""
    return {"process_failure": error.evidence()} if isinstance(error, ProcessExecutionError) else {}


def exact_refresh_command(root: Path, head: str) -> str:
    """Render the authorized refresh request bound to one lane head."""
    return (
        "ethos lane refresh-base --apply --authorize "
        f"--expect-head {head} --root {shlex.quote(root.resolve().as_posix())} --json"
    )


def with_refresh_action(root: Path, report: dict[str, object], *, apply: bool) -> dict[str, object]:
    """Attach the operation-owned continuation before CLI projection."""
    gaps = tuple(str(item) for item in cast("list[object]", report.get("required_gaps", [])))
    state = str(report.get("state") or "")
    exact_refresh = exact_refresh_command(root, str(report.get("head") or ""))
    if report.get("next_action"):
        action = str(report["next_action"])
    elif not gaps and state == "ready_to_refresh_base":
        action = exact_refresh
    elif not gaps:
        action = f"ethos land --root {shlex.quote(root.resolve().as_posix())} --json"
    elif "authorization_required" in gaps:
        action = exact_refresh
    else:
        action = f"ethos status --root {shlex.quote(root.resolve().as_posix())} --json"
    return report | {
        "next_action": action,
        "user_decision_required": (
            (not apply and state == "ready_to_refresh_base") or "authorization_required" in gaps
        ),
    }
