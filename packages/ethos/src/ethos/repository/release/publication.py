"""Read declared equal-remote publication policy."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_DEFAULTS = {"gitlab": "origin", "github": "github"}
_PEERS = {
    "gitlab": ("organization_collaboration", ".gitlab-ci.yml"),
    "github": ("public_distribution", ".github/workflows/ci.yml"),
}
_CAPABILITIES = ["repository", "ci_cd", "publication"]
_PEER_COUNT = len(_DEFAULTS)
_REMOTE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def publication_topology(config: Mapping[str, Any]) -> dict[str, object]:
    """Project compact peers or validate the verbose compatibility form."""
    raw = config.get("publication")
    if raw is None:
        return _topology(legacy=True, remotes={"origin": "origin"}, gaps=())
    if not isinstance(raw, Mapping):
        return _topology(
            legacy=False, remotes={}, gaps=("publication_topology_declaration_invalid",)
        )
    remotes, gaps = _declared_remotes(raw)
    return _topology(legacy=False, remotes=remotes, gaps=gaps)


def publication_branch_admission(
    topology: Mapping[str, object], *, branch: str, candidate_branch: str, **policy: object
) -> dict[str, object]:
    """Allow only declared targets and remote-eligible branches."""
    accepted_branch = str(policy.get("accepted_branch") or "dev")
    release_branch = str(policy.get("release_branch") or "main")
    submit_branch_prefix = str(policy.get("submit_branch_prefix") or "submit/")
    remote_name = str(policy.get("remote_name") or "origin")
    enforce = bool(policy.get("enforce", True))
    legacy = bool(topology.get("legacy"))
    gaps = [] if legacy or not enforce else _strings(topology.get("required_gaps"))
    if branch == candidate_branch:
        gaps.append(f"publication_candidate_branch_remote_forbidden:{branch}")
    elif (
        not legacy
        and branch not in {accepted_branch, release_branch}
        and not branch.startswith(submit_branch_prefix)
    ):
        gaps.append(f"publication_remote_branch_forbidden:{branch}")
    elif not remote_name:
        gaps.append("publication_remote_name_missing")
    elif not legacy and remote_name not in topology_remotes(topology).values():
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
    """Return provider IDs and their declared Git remote names."""
    return {
        key: str(_mapping(topology.get(key)).get("git_remote") or default)
        for key, default in _DEFAULTS.items()
    }


def _declared_remotes(
    raw: Mapping[str, object],
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Read compact fields or validate verbose compatibility records."""
    values = raw.get("remotes")
    if isinstance(values, list):
        remotes = dict(zip(_DEFAULTS, map(str, values), strict=False))
        return remotes, tuple(_remote_name_gaps(remotes))
    fields = {key: str(raw.get(f"{key}_remote") or "") for key in _DEFAULTS}
    if any(fields.values()):
        return fields, tuple(_remote_name_gaps(fields))
    records = raw.get("remote")
    if not isinstance(records, list):
        return {}, ("publication_topology_declaration_invalid",)
    records = {str(item.get("id") or ""): item for item in records if isinstance(item, Mapping)}
    remotes = {key: str(_mapping(records.get(key)).get("git_remote") or "") for key in _DEFAULTS}
    expected = {key: (role, key, surface, _CAPABILITIES) for key, (role, surface) in _PEERS.items()}
    gaps = _remote_name_gaps(remotes)
    gaps.extend(
        f"publication_topology_{key}_declaration_invalid"
        for key, target in expected.items()
        if tuple(
            _mapping(records.get(key)).get(name)
            for name in ("role", "provider", "ci_surface", "capabilities")
        )
        != target
    )
    if len(records) != _PEER_COUNT:
        gaps.append(f"publication_topology_remote_count_invalid:{len(records)}")
    return remotes, tuple(dict.fromkeys(gaps))


def _remote_name_gaps(remotes: Mapping[str, str]) -> list[str]:
    gaps = [
        f"publication_topology_{key}_remote_missing"
        if not remote
        else f"publication_topology_{key}_remote_invalid:{remote}"
        for key, remote in remotes.items()
        if not remote or not _REMOTE.fullmatch(remote)
    ]
    if len(set(remotes.values())) != len(remotes):
        gaps.append("publication_topology_git_remotes_duplicate")
    return gaps


def _topology(
    *, legacy: bool, remotes: Mapping[str, str], gaps: tuple[str, ...]
) -> dict[str, object]:
    peers = {key: _peer(key, remotes.get(key, "")) for key in _DEFAULTS}
    return {
        "kind": "ethos_publication_topology",
        "state": "legacy_single_remote" if legacy else "ready" if not gaps else "invalid",
        "legacy": legacy,
        "local": {
            "id": "local",
            "role": "local_verification_install",
            "mode": "offline",
            "verification_command": "tools/ci/scripts/run-local-ci.sh",
            "installation_command": "tools/ci/scripts/run-local-install-smoke.sh",
        },
        "branch_admission": {
            "candidate_role": "local_only",
            "remote_branches": "accepted_release_submit_only",
        },
        "remotes": [{"id": "origin", "git_remote": "origin"}] if legacy else list(peers.values()),
        "gitlab": peers["gitlab"] if not legacy else {},
        "github": peers["github"] if not legacy else {},
        "required_gaps": list(gaps),
    }


def _peer(key: str, remote: str) -> dict[str, object]:
    """Render one canonical provider peer from its named remote."""
    role, surface = _PEERS[key]
    return {
        "id": key,
        "role": role,
        "provider": key,
        "git_remote": remote,
        "ci_surface": surface,
        "capabilities": _CAPABILITIES,
    }


def _mapping(value: object) -> Mapping[str, object]:
    """Return a mapping only when the external payload has mapping shape."""
    return value if isinstance(value, Mapping) else {}


def _strings(value: object) -> list[str]:
    """Return a JSON-string sequence or its empty compatibility projection."""
    return [str(item) for item in value] if isinstance(value, (list, tuple)) else []
