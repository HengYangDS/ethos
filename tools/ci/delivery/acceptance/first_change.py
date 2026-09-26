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


def prove_first_change(
    executable: Path,
    target: Path,
    *,
    environment: Mapping[str, str],
) -> str:
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
    if started_code or started.get("verdict") != "pass" or not isinstance(path, str):
        message = f"installed_first_change_lane_failed:{detail[-512:]}"
        raise RuntimeError(message)
    lane = Path(path)
    if not lane.is_dir() or lane.is_symlink():
        message = "installed_first_change_lane_missing"
        raise RuntimeError(message)
    status_code, status, diagnostic = invoke(
        lane, (str(executable), "status", "--root", str(lane), "--json"), environment=selected
    )
    if status_code or status.get("required_gaps") != [
        f"openspec_requested_change_missing:{_CHANGE}"
    ]:
        message = f"installed_first_change_status_invalid:{diagnostic[-512:]}"
        raise RuntimeError(message)
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
    return "lane_admitted"
