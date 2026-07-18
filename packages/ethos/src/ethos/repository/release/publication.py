"""Read-only publication-topology declarations and branch admission."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

LOCAL_LAYER_ROLE = "local_verification_install"
LOCAL_VERIFICATION_COMMAND = "tools/ci/scripts/run-local-ci.sh"
LOCAL_INSTALLATION_COMMAND = "tools/ci/scripts/run-local-install-smoke.sh"
GITLAB_COLLABORATION_ROLE = "organization_collaboration"
GITHUB_PUBLIC_DISTRIBUTION_ROLE = "public_distribution"
REMOTE_CAPABILITIES = ("repository", "ci_cd", "publication")
_REMOTE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def publication_topology(config: Mapping[str, Any]) -> dict[str, object]:
    """Normalize explicit equal remotes, or retain a compatibility projection."""
    publication = config.get("publication")
    if publication is None:
        return _legacy_topology()
    if not isinstance(publication, Mapping):
        return _topology({}, {}, [], ["publication_topology_declaration_invalid"])

    gaps: list[str] = []
    local = _local_layer(publication.get("local"), gaps)
    branch_admission = _branch_admission(publication.get("branch_admission"), gaps)
    remotes = _remotes(publication.get("remote"), gaps)
    _validate_remotes(remotes, gaps)
    return _topology(local, branch_admission, remotes, gaps)


def publication_branch_admission(
    topology: Mapping[str, object],
    *,
    branch: str,
    candidate_branch: str,
    accepted_branch: str = "dev",
    release_branch: str = "main",
    submit_branch_prefix: str = "submit/",
    remote_name: str = "origin",
    enforce: bool = True,
) -> dict[str, object]:
    """Return no-push target admission for one named destination branch."""
    allowed_branch = branch in {accepted_branch, release_branch} or branch.startswith(
        submit_branch_prefix
    )
    declared = _declared_remote_names(topology)
    topology_gaps = _strings(topology.get("required_gaps"))
    known_target = bool(remote_name) and (bool(topology.get("legacy")) or remote_name in declared)
    gaps = list(topology_gaps if enforce else ())
    if branch == candidate_branch:
        gaps.append(f"publication_candidate_branch_remote_forbidden:{branch}")
    elif enforce and not allowed_branch:
        gaps.append(f"publication_remote_branch_forbidden:{branch}")
    elif enforce and not remote_name:
        gaps.append("publication_remote_name_missing")
    elif enforce and not known_target:
        gaps.append(f"publication_remote_target_unknown:{remote_name}")
    return {
        "branch": branch,
        "candidate_branch": candidate_branch,
        "remote_name": remote_name,
        "declared_remote_names": sorted(declared),
        "remote_target_known": known_target,
        "state": "local_only"
        if branch == candidate_branch
        else "eligible"
        if not gaps
        else "forbidden",
        "remote_mutation_allowed": not gaps,
        "enforcement_gaps": list(dict.fromkeys(gaps)),
        "next_action": _admission_next_action(
            branch=branch,
            candidate_branch=candidate_branch,
            allowed_branch=allowed_branch,
            remote_name=remote_name,
            target_known=known_target,
        ),
    }


def topology_remotes(topology: Mapping[str, object]) -> dict[str, str]:
    """Return provider IDs and Git names from the shared topology read model."""
    return {
        str(remote.get("id") or ""): str(remote.get("git_remote") or "")
        for remote in _mappings(topology.get("remotes"))
        if remote.get("id")
    }


def _topology(
    local: Mapping[str, object],
    branch_admission: Mapping[str, object],
    remotes: list[dict[str, object]],
    gaps: list[str],
) -> dict[str, object]:
    by_id = {str(remote.get("id") or ""): remote for remote in remotes}
    return {
        "kind": "ethos_publication_topology",
        "state": "ready" if not gaps else "invalid",
        "legacy": False,
        "local": dict(local),
        "branch_admission": dict(branch_admission),
        "remotes": remotes,
        "gitlab": by_id.get("gitlab", {}),
        "github": by_id.get("github", {}),
        "required_gaps": list(dict.fromkeys(gaps)),
    }


def _local_layer(raw: object, gaps: list[str]) -> dict[str, object]:
    data = _mapping(raw)
    if not data:
        gaps.append("publication_topology_local_missing")
    expected = {
        "id": "local",
        "role": LOCAL_LAYER_ROLE,
        "mode": "offline",
        "verification_command": LOCAL_VERIFICATION_COMMAND,
        "installation_command": LOCAL_INSTALLATION_COMMAND,
    }
    for field, value in expected.items():
        actual = str(data.get(field) or "")
        if actual != value:
            gaps.append(f"publication_topology_local_{field}_invalid:{actual or 'missing'}")
    return {field: str(data.get(field) or "") for field in expected}


def _branch_admission(raw: object, gaps: list[str]) -> dict[str, str]:
    data = _mapping(raw)
    expected = {
        "candidate_role": "local_only",
        "remote_branches": "accepted_release_submit_only",
    }
    if not data:
        gaps.append("publication_topology_branch_admission_missing")
    for field, value in expected.items():
        actual = str(data.get(field) or "")
        if actual != value:
            gaps.append(f"publication_topology_{field}_invalid:{actual or 'missing'}")
    return {field: str(data.get(field) or "") for field in expected}


def _remotes(raw: object, gaps: list[str]) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        gaps.append("publication_topology_remotes_missing")
        return []
    remotes: list[dict[str, object]] = []
    for index, item in enumerate(raw):
        data = _mapping(item)
        if not data:
            gaps.append(f"publication_topology_remote_invalid:{index}")
            continue
        remote: dict[str, object] = {
            "id": str(data.get("id") or ""),
            "role": str(data.get("role") or ""),
            "provider": str(data.get("provider") or ""),
            "git_remote": str(data.get("git_remote") or ""),
            "ci_surface": str(data.get("ci_surface") or ""),
            "capabilities": _strings(data.get("capabilities")),
        }
        for field in ("id", "git_remote"):
            value = str(remote[field])
            if not value:
                gaps.append(f"publication_topology_{field}_missing:{index}")
            elif not _REMOTE_NAME.fullmatch(value):
                gaps.append(f"publication_topology_{field}_invalid:{value}")
        remotes.append(remote)
    return remotes


def _validate_remotes(remotes: list[dict[str, object]], gaps: list[str]) -> None:
    if len(remotes) != 2:
        gaps.append(f"publication_topology_remote_count_invalid:{len(remotes)}")
    ids = [str(remote["id"]) for remote in remotes]
    git_names = [str(remote["git_remote"]) for remote in remotes]
    if len(ids) != len(set(ids)):
        gaps.append("publication_topology_remote_ids_duplicate")
    if len(git_names) != len(set(git_names)):
        gaps.append("publication_topology_git_remotes_duplicate")
    expected = {
        "gitlab": (GITLAB_COLLABORATION_ROLE, "gitlab", ".gitlab-ci.yml"),
        "github": (
            GITHUB_PUBLIC_DISTRIBUTION_ROLE,
            "github",
            ".github/workflows/ci.yml",
        ),
    }
    for remote_id, (role, provider, ci_surface) in expected.items():
        matches = [remote for remote in remotes if remote["id"] == remote_id]
        if len(matches) != 1:
            gaps.append(f"publication_topology_{remote_id}_missing_or_duplicate")
            continue
        remote = matches[0]
        if remote["role"] != role:
            gaps.append(
                f"publication_topology_{remote_id}_role_invalid:{remote['role'] or 'missing'}"
            )
        if remote["provider"] != provider:
            gaps.append(
                f"publication_topology_{remote_id}_provider_invalid:{remote['provider'] or 'missing'}"
            )
        if remote["ci_surface"] != ci_surface:
            gaps.append(f"publication_topology_ci_surface_invalid:{remote_id}")
        if tuple(_strings(remote["capabilities"])) != REMOTE_CAPABILITIES:
            gaps.append(f"publication_topology_capabilities_invalid:{remote_id}")


def _legacy_topology() -> dict[str, object]:
    return {
        "kind": "ethos_publication_topology",
        "state": "legacy_single_remote",
        "legacy": True,
        "local": {},
        "branch_admission": {},
        "remotes": [{"id": "origin", "git_remote": "origin"}],
        "gitlab": {},
        "github": {},
        "required_gaps": [],
    }


def _declared_remote_names(topology: Mapping[str, object]) -> set[str]:
    return {
        str(remote.get("git_remote") or "")
        for remote in _mappings(topology.get("remotes"))
        if remote.get("git_remote")
    }


def _admission_next_action(**facts: object) -> str:
    if facts["branch"] == facts["candidate_branch"]:
        return "close out candidate to dev before selecting a remote publication target"
    if not facts["allowed_branch"]:
        return "select dev, main, or submit/* before selecting a remote publication target"
    if not facts["remote_name"]:
        return "name a configured remote publication target"
    if not facts["target_known"]:
        return "select a declared GitLab or GitHub remote target"
    return "select and authorize one explicit remote publication target"


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _mappings(value: object) -> list[Mapping[str, object]]:
    return [_mapping(item) for item in value] if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, (list, tuple)) else []
