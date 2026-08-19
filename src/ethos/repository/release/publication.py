"""Compile one explicit repository-native publication topology."""

from __future__ import annotations

import os
import re
import shlex
import shutil
from collections.abc import Mapping
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any
from typing import cast

from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_OTHER
from ethos.contracts.branch.roles import ROLE_PROPOSAL_LANE
from ethos.contracts.branch.roles import ROLE_RELEASE_ROOT
from ethos.contracts.branch.roles import BranchRolePolicy

_REMOTE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_LOCAL_FIELDS = ("local_verification_command", "local_installation_command")
_DECLARATION_FIELDS = frozenset((*_LOCAL_FIELDS, "peers"))
_PEER_FIELDS = frozenset(("id", "provider", "role", "git_remote", "capabilities", "ci_surface"))
_REQUIRED_CAPABILITIES = frozenset(("repository", "publication"))
_ALLOWED_CAPABILITIES = frozenset((*_REQUIRED_CAPABILITIES, "ci_cd"))
_BRANCH_PUBLICATION_ROLES = frozenset((ROLE_ACCEPTED_ROOT, ROLE_PROPOSAL_LANE, ROLE_RELEASE_ROOT))
_RELEASE_PUBLICATION = "release_publication"
_REPOSITORY_PROOF_ROLES = frozenset((ROLE_ACCEPTED_ROOT, ROLE_RELEASE_ROOT, _RELEASE_PUBLICATION))


def publication_proof_selection(role: str) -> str:
    """Return the sole proof selection mode for one publication lifecycle role."""
    return "repository_transition" if role in _REPOSITORY_PROOF_ROLES else "current_commitment"


def publication_topology(root: Path, config: Mapping[str, Any]) -> dict[str, object]:
    """Compile and validate the repository's sole publication declaration."""
    raw = config.get("publication")
    if not isinstance(raw, Mapping) or set(raw) - _DECLARATION_FIELDS:
        return _topology(local={}, peers=(), gaps=("publication_topology_declaration_invalid",))
    if any(not isinstance(raw.get(field), str) for field in _LOCAL_FIELDS):
        return _topology(local={}, peers=(), gaps=("publication_topology_declaration_invalid",))
    raw_peers = raw.get("peers", [])
    if not isinstance(raw_peers, list):
        return _topology(local={}, peers=(), gaps=("publication_topology_declaration_invalid",))
    local = {field: str(raw.get(field) or "") for field in _LOCAL_FIELDS}
    peers: list[dict[str, object]] = []
    gaps = _local_path_gaps(root, local)
    for index, raw_peer in enumerate(raw_peers):
        peer, peer_gaps = _compile_peer(root, raw_peer, index=index)
        peers.append(peer)
        gaps.extend(peer_gaps)
    gaps.extend(_duplicate_peer_gaps(peers))
    return _topology(local=local, peers=tuple(peers), gaps=tuple(dict.fromkeys(gaps)))


def publication_ref_admission(
    topology: Mapping[str, object],
    *,
    policy: BranchRolePolicy,
    target_ref: str,
    release_tags: tuple[str, ...],
    remote_name: str,
) -> dict[str, object]:
    """Resolve and admit one complete remote ref through the positive topology."""
    gaps = _strings(topology.get("required_gaps"))
    if target_ref.startswith("refs/heads/"):
        ref_kind = "branch"
        role = policy.role_for_branch(target_ref.removeprefix("refs/heads/"))
        allowed = role in _BRANCH_PUBLICATION_ROLES
    elif target_ref.startswith("refs/tags/"):
        ref_kind = "tag"
        tag = target_ref.removeprefix("refs/tags/")
        allowed = any(fnmatchcase(tag, pattern) for pattern in release_tags)
        role = _RELEASE_PUBLICATION if allowed else ROLE_OTHER
    else:
        ref_kind = "unknown"
        role = ROLE_OTHER
        allowed = False
    if not allowed:
        gaps.append(f"publication_ref_unavailable:{ref_kind}:{role}:{target_ref}")
    elif not remote_name:
        gaps.append("publication_remote_name_missing")
    elif not gaps and remote_name not in topology_remotes(topology).values():
        gaps.append(f"publication_remote_target_unknown:{remote_name}")
    gaps = list(dict.fromkeys(gaps))
    return {
        "target_ref": target_ref,
        "ref_kind": ref_kind,
        "role": role,
        "proof_selection": publication_proof_selection(role),
        "allowed_effect": "git.ref.compare-and-swap" if allowed else "",
        "remote_name": remote_name,
        "declared_remote_names": sorted(set(topology_remotes(topology).values())),
        "remote_mutation_allowed": not gaps,
        "state": "eligible" if not gaps else "unavailable",
        "enforcement_gaps": gaps,
    }


def publication_ref_transition(
    admission: Mapping[str, object],
    *,
    observed: str,
    desired: str,
    zero: str,
    fast_forward: bool,
) -> dict[str, object]:
    """Resolve one observed ref into the sole admitted exact-CAS transition."""
    ref_kind = str(admission.get("ref_kind") or "unknown")
    admitted = admission.get("remote_mutation_allowed") is True
    current = observed == desired
    create = observed == zero
    advance = ref_kind == "branch" and fast_forward
    eligible = admitted and (current or create or advance)
    state = (
        "current"
        if admitted and current
        else "create"
        if admitted and create
        else "advance"
        if admitted and advance
        else "divergent"
        if admitted
        else "unavailable"
    )
    return {
        "target_ref": str(admission.get("target_ref") or ""),
        "ref_kind": ref_kind,
        "role": str(admission.get("role") or ROLE_OTHER),
        "observed": observed,
        "desired": desired,
        "state": state,
        "effect_allowed": eligible,
    }


def topology_remotes(topology: Mapping[str, object]) -> dict[str, str]:
    """Return peer IDs and their explicitly declared Git remote names."""
    remotes = topology.get("remotes")
    rows = remotes if isinstance(remotes, list) else []
    return {
        str(peer.get("id") or ""): str(peer.get("git_remote") or "")
        for peer in rows
        if isinstance(peer, Mapping) and peer.get("id") and peer.get("git_remote")
    }


def _compile_peer(root: Path, raw: object, *, index: int) -> tuple[dict[str, object], list[str]]:
    if not isinstance(raw, Mapping) or set(raw) - _PEER_FIELDS:
        return {}, [f"publication_topology_peer_declaration_invalid:{index}"]
    if any(
        not isinstance(raw.get(field), str) for field in ("id", "provider", "role", "git_remote")
    ) or not isinstance(raw.get("capabilities"), list):
        return {}, [f"publication_topology_peer_declaration_invalid:{index}"]
    peer_id = str(raw.get("id") or "")
    provider = str(raw.get("provider") or "")
    role = str(raw.get("role") or "")
    remote = str(raw.get("git_remote") or "")
    raw_capabilities = cast("list[object]", raw.get("capabilities"))
    if any(not isinstance(item, str) for item in raw_capabilities):
        return {}, [f"publication_topology_peer_declaration_invalid:{index}"]
    capabilities = list(dict.fromkeys(str(item) for item in raw_capabilities))
    ci_surface = raw.get("ci_surface", "")
    if not isinstance(ci_surface, str):
        return {}, [f"publication_topology_peer_declaration_invalid:{index}"]
    peer = {
        "id": peer_id,
        "provider": provider,
        "role": role,
        "git_remote": remote,
        "ci_surface": ci_surface,
        "capabilities": capabilities,
    }
    return peer, _peer_gaps(root, peer)


def _peer_gaps(root: Path, peer: Mapping[str, object]) -> list[str]:
    peer_id = str(peer["id"])
    gaps = [
        f"publication_topology_peer_{field}_invalid:{value}"
        for field in ("id", "provider", "role")
        if not (value := str(peer[field])) or _IDENTIFIER.fullmatch(value) is None
    ]
    remote = str(peer["git_remote"])
    if not remote or _REMOTE.fullmatch(remote) is None:
        gaps.append(f"publication_topology_peer_git_remote_invalid:{remote}")
    capabilities = set(cast("list[str]", peer["capabilities"]))
    if not _REQUIRED_CAPABILITIES.issubset(capabilities) or capabilities - _ALLOWED_CAPABILITIES:
        gaps.append(f"publication_topology_peer_capabilities_invalid:{peer_id}")
    ci_surface = str(peer["ci_surface"])
    if "ci_cd" in capabilities:
        gap = _peer_ci_surface_gap(root, peer_id, ci_surface)
        if gap:
            gaps.append(gap)
    elif ci_surface:
        gaps.append(f"publication_topology_peer_ci_surface_without_capability:{peer_id}")
    return gaps


def _peer_ci_surface_gap(root: Path, peer_id: str, ci_surface: str) -> str:
    return (
        f"publication_topology_peer_ci_surface_missing:{peer_id}"
        if not ci_surface
        else _repository_path_gap(
            root,
            f"peer_ci_surface:{peer_id}",
            ci_surface,
            executable=False,
        )
    )


def _duplicate_peer_gaps(peers: list[dict[str, object]]) -> list[str]:
    gaps: list[str] = []
    for field in ("id", "git_remote"):
        values = [str(peer.get(field) or "") for peer in peers if peer.get(field)]
        gaps.extend(
            f"publication_topology_peer_{field}_duplicate:{value}"
            for value in dict.fromkeys(values)
            if values.count(value) > 1
        )
    return gaps


def _local_path_gaps(root: Path, values: Mapping[str, str]) -> list[str]:
    return [
        gap
        for field in _LOCAL_FIELDS
        if (gap := _repository_path_gap(root, field, values[field], executable=True))
    ]


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


def _topology(
    *, local: Mapping[str, str], peers: tuple[dict[str, object], ...], gaps: tuple[str, ...]
) -> dict[str, object]:
    return {
        "kind": "ethos_publication_topology",
        "state": "ready" if not gaps else "invalid",
        "local": {
            "id": "local",
            "role": "local_verification_install",
            "mode": "offline",
            "verification_command": local.get("local_verification_command", ""),
            "installation_command": local.get("local_installation_command", ""),
        },
        "ref_admission": {
            "branch_roles": sorted(_BRANCH_PUBLICATION_ROLES),
            "tag_role": _RELEASE_PUBLICATION,
            "allowed_effect": "git.ref.compare-and-swap",
        },
        "remotes": list(peers),
        "required_gaps": list(gaps),
    }


def _strings(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, (list, tuple)) else []
