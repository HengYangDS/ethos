"""Compile one explicit repository-native publication topology."""

from __future__ import annotations

import os
import re
import shlex
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from typing import cast

_PROVIDERS = {
    "gitlab": "organization_collaboration",
    "github": "public_distribution",
}
_CAPABILITIES = ["repository", "ci_cd", "publication"]
_REMOTE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_LOCAL_FIELDS = ("local_verification_command", "local_installation_command")
_PROVIDER_FIELDS = tuple(
    field for provider in _PROVIDERS for field in (f"{provider}_remote", f"{provider}_ci_surface")
)
_DECLARATION_FIELDS = frozenset((*_LOCAL_FIELDS, *_PROVIDER_FIELDS))


def publication_topology(root: Path, config: Mapping[str, Any]) -> dict[str, object]:
    """Compile and validate the repository's sole publication declaration."""
    raw = config.get("publication")
    if not isinstance(raw, Mapping) or set(raw) - _DECLARATION_FIELDS:
        return _topology(values={}, gaps=("publication_topology_declaration_invalid",))
    if any(not isinstance(raw.get(field), str) for field in raw):
        return _topology(values={}, gaps=("publication_topology_declaration_invalid",))
    values = {field: str(raw.get(field) or "") for field in _DECLARATION_FIELDS}
    gaps = [*_remote_gaps(values), *_path_gaps(root, values)]
    return _topology(values=values, gaps=tuple(gaps))


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
        for provider in _PROVIDERS
    }


def _remote_gaps(values: Mapping[str, str]) -> list[str]:
    remotes = {provider: values[f"{provider}_remote"] for provider in _PROVIDERS}
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


def _path_gaps(root: Path, values: Mapping[str, str]) -> list[str]:
    gaps = []
    for field in (*_LOCAL_FIELDS, *(f"{provider}_ci_surface" for provider in _PROVIDERS)):
        value = values[field]
        kind = "command" if field in _LOCAL_FIELDS else "surface"
        gap = _repository_path_gap(root, field, value, executable=kind == "command")
        if gap:
            gaps.append(gap)
    return gaps


def _repository_path_gap(root: Path, field: str, value: str, *, executable: bool) -> str:
    prefix = f"publication_topology_{field}"
    if not value:
        return f"{prefix}_missing"
    try:
        argv = shlex.split(value) if executable else [value]
    except ValueError:
        return f"{prefix}_invalid:{value}"
    return _resolved_path_gap(root, prefix, value, argv, executable=executable)


def _resolved_path_gap(
    root: Path, prefix: str, value: str, argv: list[str], *, executable: bool
) -> str:
    if not argv:
        return f"{prefix}_missing"
    relative, resolved_root = Path(argv[0]), root.resolve()
    resolved = (resolved_root / relative).resolve()
    if relative.is_absolute() or not resolved.is_relative_to(resolved_root):
        return f"{prefix}_path_escape:{value}"
    if not resolved.exists():
        return "" if executable and shutil.which(argv[0]) else f"{prefix}_missing:{value}"
    if not resolved.is_file():
        return f"{prefix}_not_regular:{value}"
    return (
        f"{prefix}_not_executable:{value}"
        if executable and not os.access(resolved, os.X_OK)
        else ""
    )


def _topology(*, values: Mapping[str, str], gaps: tuple[str, ...]) -> dict[str, object]:
    peers = {provider: _peer(provider, values) for provider in _PROVIDERS}
    return {
        "kind": "ethos_publication_topology",
        "state": "ready" if not gaps else "invalid",
        "local": {
            "id": "local",
            "role": "local_verification_install",
            "mode": "offline",
            "verification_command": values.get("local_verification_command", ""),
            "installation_command": values.get("local_installation_command", ""),
        },
        "branch_admission": {
            "candidate_role": "local_only",
            "remote_branches": "accepted_release_proposal_only",
        },
        "remotes": list(peers.values()),
        **peers,
        "required_gaps": list(gaps),
    }


def _peer(provider: str, values: Mapping[str, str]) -> dict[str, object]:
    return {
        "id": provider,
        "role": _PROVIDERS[provider],
        "provider": provider,
        "git_remote": values.get(f"{provider}_remote", ""),
        "ci_surface": values.get(f"{provider}_ci_surface", ""),
        "capabilities": _CAPABILITIES,
    }


def _mapping(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", value) if isinstance(value, Mapping) else {}


def _strings(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, (list, tuple)) else []
