"""Exercise the first official Change through a formed project's installed Work Lane."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from tools.ci.delivery.acceptance.invocation import invoke

if TYPE_CHECKING:
    from collections.abc import Mapping

_CHANGE = "first-change"
_ROOT = f"openspec/changes/{_CHANGE}"
_CONTENT = {
    f"{_ROOT}/proposal.md": (
        "## Why\n\nEstablish the first governed capability.\n\n"
        "## What Changes\n\n- Add one foundation capability.\n"
    ),
    f"{_ROOT}/design.md": (
        "## Context\n\nFirst governed capability.\n\n## Decision\n\nUse one official Change.\n"
    ),
    f"{_ROOT}/tasks.md": "## 1. Foundation\n\n- [x] 1.1 Verify first capability.\n",
    f"{_ROOT}/specs/foundation/spec.md": (
        "## ADDED Requirements\n\n### Requirement: First capability\n\n"
        "The project SHALL retain its first governed capability.\n\n"
        "#### Scenario: A first change is proposed\n\n"
        "- **WHEN** the first Change is reviewed\n"
        "- **THEN** the new capability is visible\n"
    ),
}


def _admitted(root: Path, executable: Path, environment: Mapping[str, str], *paths: str) -> None:
    command = (
        str(executable),
        "lane",
        "prewrite",
        *paths,
        "--editor-root",
        str(root),
        "--require-editor-root",
        "--root",
        str(root),
        "--json",
    )
    code, report, detail = invoke(root, command, environment=environment)
    if code or report.get("verdict") != "pass":
        message = f"installed_first_change_prewrite_failed:{detail[-512:]}"
        raise RuntimeError(message)


def _official_command(status: dict[str, object], environment: Mapping[str, str]) -> tuple[str, str]:
    context = status.get("governance_context")
    native = context.get("official_openspec") if isinstance(context, dict) else None
    guidance = context.get("agent_guidance") if isinstance(context, dict) else None
    command = native.get("base_command") if isinstance(native, dict) else None
    guide = guidance.get("path") if isinstance(guidance, dict) else None
    package = (
        Path(guide).resolve().parents[3]
        if isinstance(guide, str)
        and Path(guide).is_absolute()
        and Path(guide).parts[-4:] == ("data", "skills", "ethos-repository-work", "SKILL.md")
        else None
    )
    if (
        not isinstance(command, list)
        or len(command) != 2
        or not all(isinstance(part, str) and Path(part).is_file() for part in command)
        or package is None
        or not Path(command[1]).resolve().is_relative_to(package)
        or shutil.which("openspec", path=environment.get("PATH", "")) is not None
    ):
        message = "installed_first_change_tool_unavailable"
        raise RuntimeError(message)
    return command[0], command[1]


def _handoff(
    executable: Path,
    lane: Path,
    started: dict[str, object],
    environment: Mapping[str, str],
    source_actor: str,
) -> tuple[dict[str, object], dict[str, str]]:
    """Transfer one exact Lease, then let only the new Agent continue."""
    lease = started.get("lease")
    branch = started.get("branch")
    if (
        not isinstance(lease, dict)
        or not isinstance(lease.get("generation"), int)
        or not isinstance(lease.get("expires_at"), str)
        or not isinstance(branch, str)
    ):
        message = "installed_first_change_lease_invalid"
        raise TypeError(message)
    successor = "agent:test:package-only:successor"
    source_env = {**environment, "ETHOS_ACTOR": source_actor, "ETHOS_CHANGE": _CHANGE}
    successor_env = {**environment, "ETHOS_ACTOR": successor, "ETHOS_CHANGE": _CHANGE}
    request = (
        str(executable),
        "lane",
        "handoff",
        "transfer",
        "--generation",
        str(lease["generation"]),
        "--expires-at",
        lease["expires_at"],
        "--branch",
        branch,
        "--holder-ref",
        source_actor,
        "--target-holder-ref",
        successor,
        "--root",
        str(lane),
    )
    code, preview, detail = invoke(lane, (*request, "--json"), environment=source_env)
    if code or (preview.get("verdict"), preview.get("state")) != ("pass", "planned"):
        message = f"installed_first_change_handoff_preview_failed:{detail[-512:]}"
        raise RuntimeError(message)
    code, applied, detail = invoke(lane, (*request, "--apply", "--json"), environment=source_env)
    output = applied.get("data")
    transferred = output.get("lease") if isinstance(output, dict) else None
    if (
        code
        or (applied.get("verdict"), applied.get("state")) != ("pass", "transferred")
        or not isinstance(transferred, dict)
        or transferred.get("holder_ref") != successor
        or transferred.get("generation") != lease["generation"] + 1
    ):
        message = f"installed_first_change_handoff_failed:{detail[-512:]}"
        raise RuntimeError(message)
    command = (str(executable), "status", "--root", str(lane), "--json")
    old_code, old, diagnostic = invoke(lane, command, environment=source_env)
    if old_code or old.get("required_gaps") != [f"lease_holder_mismatch:{branch}"]:
        message = f"installed_first_change_old_holder_not_fenced:{diagnostic[-512:]}"
        raise RuntimeError(message)
    new_code, current, diagnostic = invoke(lane, command, environment=successor_env)
    if new_code or current.get("required_gaps") != [f"openspec_requested_change_missing:{_CHANGE}"]:
        message = f"installed_first_change_successor_status_invalid:{diagnostic[-512:]}"
        raise RuntimeError(message)
    return current, successor_env


def prove_first_change(
    executable: Path,
    target: Path,
    *,
    environment: Mapping[str, str],
) -> dict[str, str]:
    """Prove first ADDED intent and write admission without source or candidate edits."""
    actor = "agent:test:package-only:formation"
    selected = {**environment, "ETHOS_ACTOR": actor, "ETHOS_CHANGE": _CHANGE}
    started_code, started, detail = invoke(
        target,
        (
            str(executable),
            "lane",
            "start",
            _CHANGE,
            "--holder-ref",
            actor,
            "--root",
            str(target),
            "--apply",
            "--json",
        ),
        environment=selected,
    )
    data = started.get("data")
    path = data.get("path") if isinstance(data, dict) else None
    if (
        started_code
        or started.get("verdict") != "pass"
        or not isinstance(data, dict)
        or not isinstance(path, str)
    ):
        message = f"installed_first_change_lane_failed:{detail[-512:]}"
        raise RuntimeError(message)
    lane = Path(path)
    if not lane.is_dir() or lane.is_symlink():
        message = "installed_first_change_lane_missing"
        raise RuntimeError(message)
    status, selected = _handoff(executable, lane, data, environment, actor)
    command = _official_command(status, selected)
    _admitted(lane, executable, selected, f"{_ROOT}/.openspec.yaml")
    created = run_command(
        lane,
        (*command, "new", "change", _CHANGE),
        env=selected,
        inherit_environment=False,
        timeout=60,
    )
    if created.returncode or not (lane / _ROOT / ".openspec.yaml").is_file():
        message = f"installed_first_change_failed:{created.stderr[-256:]}"
        raise RuntimeError(message)
    _admitted(lane, executable, selected, *_CONTENT)
    for relative, content in _CONTENT.items():
        path = lane / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    validated = run_command(
        lane,
        (*command, "validate", _CHANGE, "--strict", "--json"),
        env=selected,
        inherit_environment=False,
        timeout=60,
    )
    try:
        report = json.loads(validated.stdout)
        summary = report["summary"]["totals"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        message = "installed_first_change_validation_invalid"
        raise RuntimeError(message) from error
    if (
        validated.returncode
        or validated.stderr
        or summary
        != {
            "items": 1,
            "passed": 1,
            "failed": 0,
        }
    ):
        message = f"installed_first_change_validation_failed:{validated.stderr[-256:]}"
        raise RuntimeError(message)
    _admitted(lane, executable, selected, f"{_ROOT}/specs/foundation/spec.md")
    return {"first_change": "lane_admitted", "agent_handoff": "passed"}
