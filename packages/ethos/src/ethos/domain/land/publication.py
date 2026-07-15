"""Publication and local-CI fallback reducers for the land tail."""

from __future__ import annotations

import json
import re
from fnmatch import fnmatchcase
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ethos_core.contracts.branch.roles import BranchRolePolicy


def remote_publication_deferred(
    remote_availability: Mapping[str, object] | None = None,
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
_LOCAL_FALLBACK_UNPROBED = (
    "remote availability not probed; local-ci fallback evidence is current at HEAD"
)
_LOCAL_FALLBACK_UNAVAILABLE = "remote unavailable; local-ci fallback evidence is current at HEAD"
_LOCAL_FALLBACK_OBSERVED = (
    "remote availability observed; local-ci fallback evidence is current at HEAD"
)


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
            next_action = _LOCAL_FALLBACK_UNPROBED
        elif remote_availability_state in {"unavailable", "unconfigured"}:
            next_action = _LOCAL_FALLBACK_UNAVAILABLE
        else:
            next_action = _LOCAL_FALLBACK_OBSERVED
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
    remote_availability: Mapping[str, object] | None = None,
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


def _string_list(value: object) -> list[str]:
    """Normalize a declared list without trusting an untyped projection."""
    return [str(item) for item in value] if isinstance(value, list) else []


def publication_topology_readiness(
    *,
    topology: Mapping[str, object] | None = None,
    gitlab_availability: Mapping[str, object] | None = None,
    github_availability: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Project peer complete provider planes without claiming either outcome."""
    declared = topology or {}
    gitlab = declared.get("gitlab")
    github = declared.get("github")
    local = declared.get("local")
    gitlab = gitlab if isinstance(gitlab, dict) else {}
    github = github if isinstance(github, dict) else {}
    local = local if isinstance(local, dict) else {}
    gitlab_available = bool((gitlab_availability or {}).get("available") is True)
    github_available = bool((github_availability or {}).get("available") is True)
    gitlab_capabilities = _string_list(gitlab.get("capabilities"))
    github_capabilities = _string_list(github.get("capabilities"))
    required_capabilities = ["repository", "ci_cd", "update", "distribution"]
    raw_ref_policy = declared.get("remote_ref_policy")
    ref_policy = raw_ref_policy if isinstance(raw_ref_policy, dict) else {}
    accepted_branches = _string_list(ref_policy.get("accepted_branches"))
    excluded_branches = _string_list(ref_policy.get("excluded_branches"))
    parity = set(gitlab_capabilities) == set(required_capabilities) and set(
        github_capabilities
    ) == set(required_capabilities)
    available_provider_planes = [
        provider
        for provider, available in (
            ("gitlab", gitlab_available),
            ("github", github_available),
        )
        if available
    ]
    return {
        "kind": "three_layer_peer_complete_publication",
        "mode": str(declared.get("mode") or "single_remote_legacy"),
        "local": {
            "role": str(local.get("role") or "verification_and_install"),
            "remote_independent": local.get("remote_independent") is not False,
        },
        "gitlab": {
            "provider": "gitlab",
            "remote": str(gitlab.get("remote") or "origin"),
            "availability": gitlab_availability or {"state": "not_probed", "available": False},
            "role": str(gitlab.get("role") or "organization_primary_publication"),
            "capabilities": gitlab_capabilities,
        },
        "github": {
            "provider": "github",
            "remote": str(github.get("remote") or "github"),
            "availability": github_availability or {"state": "not_probed", "available": False},
            "role": str(github.get("role") or "independent_complete_repository"),
            "capabilities": github_capabilities,
        },
        "provider_capability_parity": {
            "required": required_capabilities,
            "equal": parity,
            "state": "equal" if parity else "declared_capabilities_diverge",
        },
        "remote_ref_policy": {
            "accepted_branches": accepted_branches,
            "excluded_branches": excluded_branches,
        },
        "available_provider_planes": available_provider_planes,
        "operating_state": (
            "both_provider_planes_available"
            if gitlab_available and github_available
            else "gitlab_peer_plane_available"
            if gitlab_available
            else "github_peer_plane_available"
            if github_available
            else "remote_state_not_decisive"
        ),
        "gitlab_primary_publication_claimed": False,
        "gitlab_hosted_status_claimed": False,
        "github_hosted_status_claimed": False,
        "github_repository_plane_claimed": False,
        "remote_publication_claimed": False,
        "next_action": (
            "record each provider's repository, CI/CD, and publication observations separately"
            if available_provider_planes
            else "probe GitLab and GitHub before any provider-plane decision"
        ),
    }


def local_submit_package(
    *,
    branch: str,
    submit_branch: str,
    candidate_branch: str = "candidate/dev",
    remote_availability: Mapping[str, object] | None = None,
    local_ci_fallback: Mapping[str, object] | None = None,
    remote_transition_allowed: bool = False,
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
        "required_steps": (
            [
                "fast-forward accepted root from candidate role; candidate branch is local-only",
                "run local-ci fallback when remote publication is unavailable",
            ]
            if not remote_transition_allowed and branch == candidate_branch
            else [
                "land work lane to candidate role",
                "fast-forward accepted root from candidate role",
                "run local-ci fallback when remote publication is unavailable",
                "create configured submit branch when remote publication is available",
            ]
        ),
    }


def publication_readiness(  # noqa: PLR0913, RUF100 - exact local/primary/mirror envelope preserves evidence boundaries
    *,
    branch: str,
    local_ok: bool,
    policy: BranchRolePolicy,
    remote_availability: Mapping[str, object] | None = None,
    github_availability: Mapping[str, object] | None = None,
    topology: Mapping[str, object] | None = None,
    local_ci_fallback: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Assemble publication readiness with local and peer-provider boundaries."""
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
    topology_state = publication_topology_readiness(
        topology=topology,
        gitlab_availability=availability,
        github_availability=github_availability,
    )
    remote_target_branch = submit_branch or branch
    remote_ref_policy = cast("dict[str, object]", topology_state["remote_ref_policy"])
    accepted_branches = _string_list(remote_ref_policy.get("accepted_branches"))
    excluded_branches = _string_list(remote_ref_policy.get("excluded_branches"))
    remote_transition_allowed = not accepted_branches or (
        remote_target_branch not in excluded_branches
        and any(fnmatchcase(remote_target_branch, pattern) for pattern in accepted_branches)
    )
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
    if availability.get("available") is True and remote_transition_allowed:
        next_action = "create configured submit branch when remote publication is available"
    if not remote_transition_allowed:
        next_action = (
            "candidate/dev is local-only; fast-forward dev before any remote transition"
            if branch == policy.candidate_branch
            else f"remote ref policy does not accept {remote_target_branch}"
        )
    if remote_state == "synchronized":
        next_action = "remote tracking ref is synchronized; no push was performed"
    if topology_state["available_provider_planes"] and remote_state != "synchronized":
        next_action = str(topology_state["next_action"])
    next_actions = [next_action] if local_ok else ["resolve local publish readiness gaps"]
    return {
        "mode": "local_readiness",
        "remote_push": "not_performed",
        # This is remote *publication* state, not remote reachability.
        # Reachability remains visible under remote_availability.state.
        "remote_state": remote_state,
        "remote_availability": availability,
        "remote_sync": sync,
        "github_availability": github_availability or {"state": "not_probed", "available": False},
        "gitlab_availability": availability,
        "publication_topology": topology_state,
        "remote_target_branch": remote_target_branch,
        "remote_transition_allowed": remote_transition_allowed,
        "fallback_evidence": fallback,
        "submit_branch": submit_branch,
        "local_submit_package": local_submit_package(
            branch=branch,
            submit_branch=submit_branch,
            candidate_branch=policy.candidate_branch,
            remote_availability=availability,
            local_ci_fallback=fallback,
            remote_transition_allowed=remote_transition_allowed,
        ),
        "required_gaps": [] if local_ok else ["local_publish_readiness_blocked"],
        "next_actions": next_actions,
    }
