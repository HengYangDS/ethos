"""Local CI fallback evidence: whether it is bound to the current head, and what it claims."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

from ethos.contracts.verdict import report_verdict

LOCAL_CI_FALLBACK_EVIDENCE_PATH = Path("build/evidence/local-ci/fallback.json")


def local_ci_fallback_evidence_status(
    repo: Path,
    *,
    current_head: str,
    command: str,
) -> dict[str, object]:
    """Project whether local-ci fallback evidence is bound to the current HEAD."""
    relative = LOCAL_CI_FALLBACK_EVIDENCE_PATH.as_posix()
    try:
        payload = json.loads((repo / LOCAL_CI_FALLBACK_EVIDENCE_PATH).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _evidence_status("missing", relative, current_head, command)
    except json.JSONDecodeError:
        return _evidence_status("invalid", relative, current_head, command)
    if not isinstance(payload, dict):
        return _evidence_status("invalid", relative, current_head, command)
    evidence_head = str(payload.get("head") or "")
    evidence_command = str(payload.get("command") or "")
    current = (
        bool(current_head)
        and evidence_head == current_head
        and evidence_command == command
        and report_verdict(payload) == "pass"
    )
    return {
        "state": "current" if current else "stale",
        "path": relative,
        "current_head": current_head,
        "evidence_head": evidence_head,
        "verdict": "pass" if current else "block",
        "command": evidence_command,
        "next_action": (
            "local-ci fallback evidence is current at HEAD" if current else fallback_action(command)
        ),
    }


def _evidence_status(state: str, path: str, current_head: str, command: str) -> dict[str, object]:
    """Render a missing or invalid fallback-evidence status."""
    return {
        "state": state,
        "path": path,
        "current_head": current_head,
        "evidence_head": "",
        "verdict": "block",
        "next_action": fallback_action(command, refresh=state not in {"missing", "not_checked"}),
    }


def local_ci_fallback_package(
    *,
    root: Path | None = None,
    current_head: str = "",
    command: str = "",
) -> dict[str, object]:
    """Describe local fallback evidence without claiming hosted CI success."""
    status = (
        local_ci_fallback_evidence_status(
            root,
            current_head=current_head,
            command=command,
        )
        if root
        else _evidence_status(
            "not_checked",
            LOCAL_CI_FALLBACK_EVIDENCE_PATH.as_posix(),
            current_head,
            command,
        )
    )
    return {
        "kind": "local_ci_fallback",
        "evidence_class": "local_fallback",
        "boundary": "local-ci evidence; hosted CI status unclaimed",
        "hosted_ci_status_claimed": False,
        "command": command,
        "owner_scripts": local_ci_owner_scripts(root=root, command=command),
        "evidence_status": status,
    }


def local_ci_owner_scripts(*, root: Path | None = None, command: str = "") -> list[str]:
    """Project repository scripts invoked by a repository-local command owner."""
    try:
        argv = shlex.split(command)
    except ValueError:
        return []
    if not argv:
        return []
    script = (root or Path.cwd()) / argv[0]
    if script.is_file():
        return list(
            dict.fromkeys(
                re.findall(
                    r"tools/ci/scripts/[A-Za-z0-9_.-]+\.sh",
                    script.read_text(encoding="utf-8"),
                )
            )
        )
    return []


def fallback_action(command: str, *, refresh: bool = False) -> str:
    """Name the command that produces or refreshes local fallback evidence."""
    if not command:
        return "declare .ethos/release.toml [publication].local_verification_command"
    return (
        f"rerun {command} to refresh local fallback evidence"
        if refresh
        else f"run {command} as local fallback evidence"
    )
