"""Read the declared dual-remote publication topology."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from typing import cast

_PEERS = {
    "gitlab": ("organization_collaboration", ".gitlab-ci.yml"),
    "github": ("public_distribution", ".github/workflows/ci.yml"),
}
_CAPABILITIES = ["repository", "ci_cd", "publication"]
_REMOTE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_DECLARATION_FIELDS = frozenset(f"{provider}_remote" for provider in _PEERS)


def publication_topology(config: Mapping[str, Any]) -> dict[str, object]:
    """Project the required named GitLab and GitHub remote declaration."""
    raw = config.get("publication")
    if not isinstance(raw, Mapping):
        return _topology(remotes={}, gaps=("publication_topology_declaration_invalid",))
    remotes, gaps = _declared_remotes(raw)
    return _topology(remotes=remotes, gaps=gaps)


def publication_branch_admission(
    topology: Mapping[str, object], *, branch: str, candidate_branch: str, **policy: object
) -> dict[str, object]:
    """Allow only declared targets and remote-eligible branches."""
    accepted_branch = str(policy.get("accepted_branch") or "dev")
    release_branch = str(policy.get("release_branch") or "main")
    proposal_branch_prefix = str(policy.get("proposal_branch_prefix") or "proposal/")
    remote_name = str(policy["remote_name"]) if "remote_name" in policy else "origin"
    gaps = _strings(topology.get("required_gaps"))
    if branch == candidate_branch:
        gaps.append(f"publication_candidate_branch_remote_forbidden:{branch}")
    elif branch not in {accepted_branch, release_branch} and not branch.startswith(
        proposal_branch_prefix
    ):
        gaps.append(f"publication_remote_branch_forbidden:{branch}")
    elif not remote_name:
        gaps.append("publication_remote_name_missing")
    elif not gaps and remote_name not in topology_remotes(topology).values():
        gaps.append(f"publication_remote_target_unknown:{remote_name}")
    gaps = list(dict.fromkeys(gaps))
    return {
        "branch": branch,
        "candidate_branch": candidate_branch,
        "remote_name": remote_name,
        "declared_remote_names": sorted(set(topology_remotes(topology).values()) - {""}),
        "remote_mutation_allowed": not gaps,
        "state": "local_only"
        if branch == candidate_branch
        else "eligible"
        if not gaps
        else "forbidden",
        "enforcement_gaps": gaps,
    }


def topology_remotes(topology: Mapping[str, object]) -> dict[str, str]:
    """Return provider IDs and their explicitly declared Git remote names."""
    return {
        provider: str(_mapping(topology.get(provider)).get("git_remote") or "")
        for provider in _PEERS
    }


def _declared_remotes(
    raw: Mapping[str, object],
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Read only the required named scalar remote declaration."""
    fields = set(raw)
    if fields - _DECLARATION_FIELDS:
        return {}, ("publication_topology_declaration_invalid",)
    if any(not isinstance(raw.get(field), str) for field in fields):
        return {}, ("publication_topology_declaration_invalid",)
    remotes = {provider: str(raw.get(f"{provider}_remote") or "") for provider in _PEERS}
    return remotes, tuple(_remote_name_gaps(remotes))


def _remote_name_gaps(remotes: Mapping[str, str]) -> list[str]:
    gaps = [
        f"publication_topology_{provider}_remote_missing"
        if not remote
        else f"publication_topology_{provider}_remote_invalid:{remote}"
        for provider, remote in remotes.items()
        if not remote or not _REMOTE.fullmatch(remote)
    ]
    if all(remotes.values()) and len(set(remotes.values())) != len(remotes):
        gaps.append("publication_topology_git_remotes_duplicate")
    return gaps


def _topology(*, remotes: Mapping[str, str], gaps: tuple[str, ...]) -> dict[str, object]:
    peers = {provider: _peer(provider, remotes.get(provider, "")) for provider in _PEERS}
    return {
        "kind": "ethos_publication_topology",
        "state": "ready" if not gaps else "invalid",
        "local": {
            "id": "local",
            "role": "local_verification_install",
            "mode": "offline",
            "verification_command": "tools/ci/scripts/run-local-ci.sh",
            "installation_command": "tools/ci/scripts/run-local-install-smoke.sh",
        },
        "branch_admission": {
            "candidate_role": "local_only",
            "remote_branches": "accepted_release_proposal_only",
        },
        "remotes": list(peers.values()),
        "gitlab": peers["gitlab"],
        "github": peers["github"],
        "required_gaps": list(gaps),
    }


def _peer(provider: str, remote: str) -> dict[str, object]:
    """Render one canonical provider peer from its named remote."""
    role, surface = _PEERS[provider]
    return {
        "id": provider,
        "role": role,
        "provider": provider,
        "git_remote": remote,
        "ci_surface": surface,
        "capabilities": _CAPABILITIES,
    }


def _mapping(value: object) -> Mapping[str, object]:
    """Return a mapping only when the external payload has mapping shape."""
    return cast("Mapping[str, object]", value) if isinstance(value, Mapping) else {}


def _strings(value: object) -> list[str]:
    """Return a JSON-string sequence or its empty projection."""
    return [str(item) for item in value] if isinstance(value, (list, tuple)) else []
