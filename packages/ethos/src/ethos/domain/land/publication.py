"""Publication and local-CI fallback reducers for the land tail."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from ethos_core.contracts.branch.roles import BranchRolePolicy


def remote_publication_deferred(
    remote_availability: dict[str, object] | None = None,
    *,
    root: Path | None = None,
) -> dict[str, object]:
    """Describe the deferred remote-publication state (no remote adapter success)."""
    availability = remote_availability or {
        "kind": "git_remote_availability",
        "remote": "origin",
        "state": "not_probed",
        "available": False,
        "blocking": False,
        "required_gaps": [],
        "advisory_gaps": [],
    }
    state = str(availability.get("state") or "not_probed")
    reason = (
        "remote unavailable; use local-ci fallback evidence"
        if state in {"unavailable", "unconfigured"}
        else "remote publication adapter unavailable"
    )
    return {
        "remote_push": "not_performed",
        "state": "deferred",
        "reason": reason,
        "availability": availability,
        "fallback": local_ci_fallback_package(remote_availability=availability, root=root),
    }


LOCAL_CI_FALLBACK_EVIDENCE_PATH = Path("build/evidence/local-ci/fallback.json")


def local_ci_fallback_evidence_status(
    repo: Path,
    *,
    current_head: str,
    remote_availability_state: str = "not_probed",
) -> dict[str, object]:
    """Project whether local-ci fallback evidence is bound to the current HEAD."""
    relative_path = LOCAL_CI_FALLBACK_EVIDENCE_PATH.as_posix()
    path = repo / LOCAL_CI_FALLBACK_EVIDENCE_PATH
    if not path.exists():
        return {
            "state": "missing",
            "path": relative_path,
            "current_head": current_head,
            "evidence_head": "",
            "ok": False,
            "next_action": "run tools/ci/scripts/run-local-ci.sh as local fallback evidence",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "state": "invalid",
            "path": relative_path,
            "current_head": current_head,
            "evidence_head": "",
            "ok": False,
            "next_action": (
                "rerun tools/ci/scripts/run-local-ci.sh to refresh local fallback evidence"
            ),
        }
    evidence_head = str(payload.get("head") or "")
    evidence_ok = payload.get("ok") is True
    current = bool(current_head) and evidence_head == current_head and evidence_ok
    next_action = "run tools/ci/scripts/run-local-ci.sh as local fallback evidence"
    if current:
        if remote_availability_state == "not_probed":
            next_action = (
                "remote availability not probed; local-ci fallback evidence is current at HEAD"
            )
        elif remote_availability_state in {"unavailable", "unconfigured"}:
            next_action = "remote unavailable; local-ci fallback evidence is current at HEAD"
        else:
            next_action = (
                "remote availability observed; local-ci fallback evidence is current at HEAD"
            )
    return {
        "state": "current" if current else "stale",
        "path": relative_path,
        "current_head": current_head,
        "evidence_head": evidence_head,
        "ok": current,
        "command": str(payload.get("command") or ""),
        "next_action": next_action,
    }


def local_ci_fallback_package(
    remote_availability: dict[str, object] | None = None,
    *,
    root: Path | None = None,
    current_head: str = "",
) -> dict[str, object]:
    """Describe local CI fallback evidence without claiming hosted CI success."""
    availability = remote_availability or {
        "kind": "git_remote_availability",
        "remote": "origin",
        "state": "not_probed",
        "available": False,
        "blocking": False,
    }
    evidence_status = (
        local_ci_fallback_evidence_status(
            root,
            current_head=current_head,
            remote_availability_state=str(availability.get("state") or "not_probed"),
        )
        if root is not None
        else {
            "state": "not_checked",
            "path": LOCAL_CI_FALLBACK_EVIDENCE_PATH.as_posix(),
            "current_head": current_head,
            "evidence_head": "",
            "ok": False,
            "next_action": "run tools/ci/scripts/run-local-ci.sh as local fallback evidence",
        }
    )
    return {
        "kind": "local_ci_fallback",
        "evidence_class": "local_fallback",
        "boundary": "local-ci evidence; hosted CI status unclaimed",
        "hosted_ci_status_claimed": False,
        "remote_availability_state": str(availability.get("state") or "not_probed"),
        "command": "tools/ci/scripts/run-local-ci.sh",
        "owner_scripts": local_ci_owner_scripts(root=root),
        "evidence_status": evidence_status,
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
    return [
        "tools/ci/scripts/run-python-lint.sh",
        "tools/ci/scripts/run-config-lint.sh",
        "tools/ci/scripts/run-shell-lint.sh",
        "tools/ci/scripts/run-markdown-lint.sh",
        "tools/ci/scripts/run-import-linter.sh",
        "tools/ci/scripts/run-docstring-coverage.sh",
        "tools/ci/scripts/run-module-layout.sh",
        "tools/ci/scripts/run-bandit.sh",
        "tools/ci/scripts/run-repository-hygiene.sh",
        "tools/ci/scripts/run-secrets-scan.sh",
        "tools/ci/scripts/run-ci-template-check.sh",
        "tools/ci/scripts/run-format-selection.sh",
        "tools/ci/scripts/run-architecture-projection-drift.sh",
        "tools/ci/scripts/run-runbook-registry-check.sh",
        "tools/ci/scripts/run-mcp-smoke.sh",
        "tools/ci/scripts/run-closeout-evidence-manifest.sh",
        "tools/ci/scripts/run-local-state-audit.sh",
        "tools/ci/scripts/run-release-supply-chain.sh",
        "tools/ci/scripts/run-python-tests.sh",
    ]


def local_submit_package(
    *,
    branch: str,
    submit_branch: str,
    remote_availability: dict[str, object] | None = None,
    local_ci_fallback: dict[str, object] | None = None,
) -> dict[str, object]:
    """Plan the local submit-branch package (remote push deferred)."""
    return {
        "kind": "submit_branch_plan",
        "source_branch": branch,
        "submit_branch": submit_branch,
        "remote_push": "not_performed",
        "remote_state": "deferred",
        "blocking": False,
        "remote_availability": remote_availability or {"state": "not_probed", "available": False},
        "local_ci_fallback": local_ci_fallback
        or local_ci_fallback_package(remote_availability=remote_availability),
        "required_steps": [
            "land work lane to candidate role",
            "fast-forward accepted root from candidate role",
            "run local-ci fallback when remote publication is unavailable",
            "create configured submit branch when remote publication is available",
        ],
    }


def publication_readiness(
    *,
    branch: str,
    local_ok: bool,
    policy: BranchRolePolicy,
    remote_availability: dict[str, object] | None = None,
    local_ci_fallback: dict[str, object] | None = None,
) -> dict[str, object]:
    """Assemble publication readiness with remote probe and local-ci fallback."""
    submit_branch = policy.submit_branch_for_source(branch)
    availability = remote_availability or {
        "kind": "git_remote_availability",
        "remote": "origin",
        "state": "not_probed",
        "available": False,
        "blocking": False,
        "required_gaps": [],
        "advisory_gaps": [],
    }
    sync_value = availability.get("tracking_sync")
    sync = (
        cast("dict[str, object]", sync_value)
        if isinstance(sync_value, dict)
        else {
            "kind": "git_remote_tracking_sync",
            "state": "not_checked",
            "available": False,
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [],
        }
    )
    fallback = local_ci_fallback or local_ci_fallback_package(remote_availability=availability)
    evidence_status = fallback.get("evidence_status")
    if isinstance(evidence_status, dict):
        evidence_next_action = str(
            evidence_status.get("next_action")
            or "run tools/ci/scripts/run-local-ci.sh as local fallback evidence"
        )
    else:
        evidence_next_action = "run tools/ci/scripts/run-local-ci.sh as local fallback evidence"

    # A synchronized tracking ref is a distinct observation. It confirms that the
    # locally observed remote-tracking ref matches HEAD, while `remote_push` stays
    # `not_performed` because this command never mutates a remote.
    remote_state = "synchronized" if sync.get("state") == "synchronized" else "deferred"
    next_action = evidence_next_action
    if availability.get("available") is True:
        next_action = "create configured submit branch when remote publication is available"
    if remote_state == "synchronized":
        next_action = "remote tracking ref is synchronized; no push was performed"
    next_actions = [next_action] if local_ok else ["resolve local publish readiness gaps"]
    return {
        "mode": "local_readiness",
        "remote_push": "not_performed",
        # This is remote *publication* state, not remote reachability.
        # Reachability remains visible under remote_availability.state.
        "remote_state": remote_state,
        "remote_availability": availability,
        "remote_sync": sync,
        "fallback_evidence": fallback,
        "submit_branch": submit_branch,
        "local_submit_package": local_submit_package(
            branch=branch,
            submit_branch=submit_branch,
            remote_availability=availability,
            local_ci_fallback=fallback,
        ),
        "required_gaps": [] if local_ok else ["local_publish_readiness_blocked"],
        "next_actions": next_actions,
    }


def publication_with_remote_matrix(
    publication: dict[str, object],
    matrix: dict[str, object],
    *,
    remote_available: bool,
) -> dict[str, object]:
    """Refine the publication next action without changing its compatibility shape."""
    if not remote_available or matrix.get("state") != "reconciliation_required":
        return publication
    return {
        **publication,
        "next_actions": ["reconcile diverged remotes before creating a submit branch"],
    }
