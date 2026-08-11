"""Publication and local-CI fallback reducers for the land tail."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.contracts.verdict import report_verdict

if TYPE_CHECKING:
    from ethos.contracts.branch.roles import BranchRolePolicy

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
            "local-ci fallback evidence is current at HEAD"
            if current
            else _fallback_action(command)
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
        "next_action": _fallback_action(command)
        if state in {"missing", "not_checked"}
        else _refresh_action(command),
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


def publication_readiness(
    *, branch: str, local_ok: bool, policy: BranchRolePolicy, **options: object
) -> dict[str, object]:
    """Assemble local readiness and independent no-push remote observations."""
    local_ci_fallback = options.get("local_ci_fallback")
    topology = options.get("topology")
    remote_observations = options.get("remote_observations")
    observations = {key: _object(value) for key, value in _object(remote_observations).items()}
    fallback = _object(
        local_ci_fallback,
        local_ci_fallback_package(
            command=str(options.get("local_verification_command") or ""),
        ),
    )
    fallback_command = str(
        fallback.get("command") or options.get("local_verification_command") or ""
    )
    available = [
        item
        for item in observations.values()
        if _object(item.get("availability")).get("available") is True
    ]
    synchronized = bool(observations) and all(
        _object(item.get("sync")).get("state") == "synchronized" for item in observations.values()
    )
    state = (
        "local_only"
        if not observations
        else "synchronized"
        if synchronized
        else "targets_available"
        if len(available) == len(observations) and len(observations) > 1
        else "target_available"
        if available
        else "deferred"
    )
    evidence = fallback.get("evidence_status")
    action = (
        "remote tracking ref is synchronized; no push was performed"
        if synchronized
        else "create configured proposal branch when remote publication is available"
        if available
        else str(evidence.get("next_action") or _fallback_action(fallback_command))
        if isinstance(evidence, dict)
        else _fallback_action(fallback_command)
    )
    proposal = policy.proposal_branch_for_source(branch)
    return {
        "mode": "local_readiness",
        "remote_push": "not_performed",
        "remote_state": state,
        "remote_topology": topology if isinstance(topology, dict) else {"state": "unspecified"},
        "remote_observations": observations,
        "fallback_evidence": fallback,
        "proposal_branch": proposal,
        "local_proposal_package": _proposal_package(branch, proposal, fallback),
        "required_gaps": [] if local_ok else ["local_publish_readiness_blocked"],
        "next_action": action if local_ok else "resolve local publish readiness gaps",
    }


def _proposal_package(
    branch: str,
    proposal: str,
    fallback: dict[str, object],
) -> dict[str, object]:
    """Return the local plan for a future configured proposal branch."""
    return {
        "kind": "proposal_branch_plan",
        "source_branch": branch,
        "proposal_branch": proposal,
        "remote_push": "not_performed",
        "remote_state": "deferred",
        "blocking": False,
        "local_ci_fallback": fallback,
        "required_steps": [
            "land work lane to candidate role",
            "fast-forward accepted root from candidate role",
            "run local-ci fallback when remote publication is unavailable",
            "create configured proposal branch when remote publication is available",
        ],
    }


def _object(value: object, fallback: dict[str, object] | None = None) -> dict[str, object]:
    """Return a JSON-object mapping or the supplied safe fallback."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else (fallback or {})


def _fallback_action(command: str) -> str:
    return (
        f"run {command} as local fallback evidence"
        if command
        else "declare .ethos/release.toml [publication].local_verification_command"
    )


def _refresh_action(command: str) -> str:
    return (
        f"rerun {command} to refresh local fallback evidence"
        if command
        else _fallback_action(command)
    )


def publication_with_remote_matrix(
    publication: dict[str, object], matrix: dict[str, object], *, remote_available: bool
) -> dict[str, object]:
    """Refine the no-push next action for a reconciliation requirement."""
    return (
        {
            **publication,
            "next_action": "reconcile diverged remotes before creating a proposal branch",
        }
        if remote_available and matrix.get("state") == "reconciliation_required"
        else publication
    )
