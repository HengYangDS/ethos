"""Publication and local-CI fallback reducers for the land tail."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from ethos_core.contracts.branch.roles import BranchRolePolicy

LOCAL_CI_FALLBACK_EVIDENCE_PATH = Path("build/evidence/local-ci/fallback.json")
_FALLBACK = "run tools/ci/scripts/run-local-ci.sh as local fallback evidence"
_NOT_PROBED: dict[str, object] = {
    "kind": "git_remote_availability",
    "remote": "origin",
    "state": "not_probed",
    "available": False,
    "blocking": False,
    "required_gaps": [],
    "advisory_gaps": [],
}
_NOT_CHECKED_SYNC: dict[str, object] = {
    "kind": "git_remote_tracking_sync",
    "state": "not_checked",
    "available": False,
    "blocking": False,
    "required_gaps": [],
    "advisory_gaps": [],
}
_REMOTE_PAIR = 2


def remote_publication_deferred(
    remote_availability: dict[str, object] | None = None, *, root: Path | None = None
) -> dict[str, object]:
    """Describe deferred remote publication without claiming adapter success."""
    availability = remote_availability or dict(_NOT_PROBED)
    return {
        "remote_push": "not_performed",
        "state": "deferred",
        "reason": "remote unavailable; use local-ci fallback evidence"
        if availability.get("state") in {"unavailable", "unconfigured"}
        else "remote publication adapter unavailable",
        "availability": availability,
        "fallback": local_ci_fallback_package(remote_availability=availability, root=root),
    }


def local_ci_fallback_evidence_status(
    repo: Path, *, current_head: str, remote_availability_state: str = "not_probed"
) -> dict[str, object]:
    """Project whether local-ci fallback evidence is bound to the current HEAD."""
    relative = LOCAL_CI_FALLBACK_EVIDENCE_PATH.as_posix()
    try:
        payload = json.loads((repo / LOCAL_CI_FALLBACK_EVIDENCE_PATH).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _evidence_status("missing", relative, current_head)
    except json.JSONDecodeError:
        return _evidence_status("invalid", relative, current_head)
    evidence_head = str(payload.get("head") or "")
    current = bool(current_head) and evidence_head == current_head and payload.get("ok") is True
    action = _FALLBACK
    if current:
        state = (
            "not probed"
            if remote_availability_state == "not_probed"
            else "unavailable"
            if remote_availability_state in {"unavailable", "unconfigured"}
            else "observed"
        )
        action = (
            "remote availability not probed; local-ci fallback evidence is current at HEAD"
            if state == "not probed"
            else "remote unavailable; local-ci fallback evidence is current at HEAD"
            if state == "unavailable"
            else "remote availability observed; local-ci fallback evidence is current at HEAD"
        )
    return {
        "state": "current" if current else "stale",
        "path": relative,
        "current_head": current_head,
        "evidence_head": evidence_head,
        "ok": current,
        "command": str(payload.get("command") or ""),
        "next_action": action,
    }


def _evidence_status(state: str, path: str, current_head: str) -> dict[str, object]:
    """Render a missing or invalid fallback-evidence status."""
    return {
        "state": state,
        "path": path,
        "current_head": current_head,
        "evidence_head": "",
        "ok": False,
        "next_action": _FALLBACK
        if state in {"missing", "not_checked"}
        else "rerun tools/ci/scripts/run-local-ci.sh to refresh local fallback evidence",
    }


def local_ci_fallback_package(
    remote_availability: dict[str, object] | None = None,
    *,
    root: Path | None = None,
    current_head: str = "",
) -> dict[str, object]:
    """Describe local fallback evidence without claiming hosted CI success."""
    availability = remote_availability or dict(_NOT_PROBED)
    status = (
        local_ci_fallback_evidence_status(
            root,
            current_head=current_head,
            remote_availability_state=str(availability.get("state") or "not_probed"),
        )
        if root
        else _evidence_status(
            "not_checked", LOCAL_CI_FALLBACK_EVIDENCE_PATH.as_posix(), current_head
        )
    )
    return {
        "kind": "local_ci_fallback",
        "evidence_class": "local_fallback",
        "boundary": "local-ci evidence; hosted CI status unclaimed",
        "hosted_ci_status_claimed": False,
        "remote_availability_state": str(availability.get("state") or "not_probed"),
        "command": "tools/ci/scripts/run-local-ci.sh",
        "owner_scripts": local_ci_owner_scripts(root=root),
        "evidence_status": status,
    }


def local_ci_owner_scripts(*, root: Path | None = None) -> list[str]:
    """Project owner gates invoked by the target repo's local-ci script."""
    script = (root or Path.cwd()) / "tools/ci/scripts/run-local-ci.sh"
    if script.exists():
        return list(
            dict.fromkeys(
                re.findall(
                    r"tools/ci/scripts/[A-Za-z0-9_.-]+\.sh",
                    script.read_text(encoding="utf-8"),
                )
            )
        )
    names = """run-python-lint run-config-lint run-shell-lint run-markdown-lint
run-import-linter run-docstring-coverage run-module-layout run-bandit
run-repository-hygiene run-secrets-scan run-ci-template-check run-format-selection
run-architecture-projection-drift run-runbook-registry-check run-mcp-smoke
run-closeout-evidence-manifest run-local-state-audit run-release-supply-chain
run-python-tests"""
    return [f"tools/ci/scripts/{name}.sh" for name in names.split()]


def publication_readiness(
    *, branch: str, local_ok: bool, policy: BranchRolePolicy, **options: object
) -> dict[str, object]:
    """Assemble local readiness and independent no-push remote observations."""
    remote_availability = options.get("remote_availability")
    local_ci_fallback = options.get("local_ci_fallback")
    topology = options.get("topology")
    remote_observations = options.get("remote_observations")
    availability = _object(remote_availability, _NOT_PROBED)
    sync = (
        _object(availability.get("tracking_sync"))
        if isinstance(availability.get("tracking_sync"), dict)
        else dict(_NOT_CHECKED_SYNC)
    )
    observations = {
        key: _object(value)
        for key, value in _object(
            remote_observations,
            {"gitlab": {"availability": availability, "sync": sync}},
        ).items()
    }
    primary = observations.get("gitlab", {})
    availability, sync = (
        _object(primary.get("availability"), availability),
        _object(primary.get("sync"), sync),
    )
    fallback = _object(
        local_ci_fallback,
        local_ci_fallback_package(remote_availability=availability),
    )
    available = [
        item
        for item in observations.values()
        if _object(item.get("availability")).get("available") is True
    ]
    synchronized = any(
        _object(item.get("sync")).get("state") == "synchronized" for item in observations.values()
    )
    state = (
        "synchronized"
        if synchronized
        else "targets_available"
        if remote_observations and len(available) == _REMOTE_PAIR
        else "target_available"
        if remote_observations and available
        else "deferred"
    )
    evidence = fallback.get("evidence_status")
    action = (
        "remote tracking ref is synchronized; no push was performed"
        if synchronized
        else "create configured submit branch when remote publication is available"
        if available
        else str(evidence.get("next_action") or _FALLBACK)
        if isinstance(evidence, dict)
        else _FALLBACK
    )
    submit = policy.submit_branch_for_source(branch)
    return {
        "mode": "local_readiness",
        "remote_push": "not_performed",
        "remote_state": state,
        "remote_availability": availability,
        "remote_sync": sync,
        "remote_topology": topology if isinstance(topology, dict) else {"legacy": True},
        "remote_observations": observations,
        "fallback_evidence": fallback,
        "submit_branch": submit,
        "local_submit_package": _submit_package(branch, submit, availability, fallback),
        "required_gaps": [] if local_ok else ["local_publish_readiness_blocked"],
        "next_actions": [action] if local_ok else ["resolve local publish readiness gaps"],
    }


def _submit_package(
    branch: str,
    submit: str,
    availability: dict[str, object],
    fallback: dict[str, object],
) -> dict[str, object]:
    """Return the local plan for a future configured submit branch."""
    return {
        "kind": "submit_branch_plan",
        "source_branch": branch,
        "submit_branch": submit,
        "remote_push": "not_performed",
        "remote_state": "deferred",
        "blocking": False,
        "remote_availability": availability,
        "local_ci_fallback": fallback,
        "required_steps": [
            "land work lane to candidate role",
            "fast-forward accepted root from candidate role",
            "run local-ci fallback when remote publication is unavailable",
            "create configured submit branch when remote publication is available",
        ],
    }


def local_submit_package(
    *,
    branch: str,
    submit_branch: str,
    remote_availability: dict[str, object] | None = None,
    local_ci_fallback: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return the public compatibility projection of the local submit plan."""
    availability = remote_availability or dict(_NOT_PROBED)
    fallback = local_ci_fallback or local_ci_fallback_package(remote_availability=availability)
    return _submit_package(branch, submit_branch, availability, fallback)


def _object(value: object, fallback: dict[str, object] | None = None) -> dict[str, object]:
    """Return a JSON-object mapping or the supplied safe fallback."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else (fallback or {})


def publication_with_remote_matrix(
    publication: dict[str, object], matrix: dict[str, object], *, remote_available: bool
) -> dict[str, object]:
    """Refine the no-push next action for a reconciliation requirement."""
    return (
        {
            **publication,
            "next_actions": ["reconcile diverged remotes before creating a submit branch"],
        }
        if remote_available and matrix.get("state") == "reconciliation_required"
        else publication
    )
