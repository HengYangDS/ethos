"""Committed repository profile observation adapter."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import read_objects
from ethos.adapters.repo.git_object import resolve_revisions
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import repository_profile_from_text

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def load_committed_repository_profile(
    root: Path,
    tree_ref: str,
    *,
    environment: Mapping[str, str] | None = None,
) -> RepositoryProfile:
    """Load one profile from an exact committed Git tree."""
    result = run_git(
        root,
        "show",
        f"{tree_ref}:.ethos/profile.toml",
        check=False,
        env=environment,
    )
    if result.returncode == 0:
        return repository_profile_from_text(root, exists=True, text=result.stdout)
    commit = run_git(
        root,
        "rev-parse",
        "--verify",
        f"{tree_ref}^{{commit}}",
        check=False,
        env=environment,
    )
    if commit.returncode == 0:
        return repository_profile_from_text(root, exists=False, text="")
    message = "repository_tree_ref_invalid"
    raise ValueError(message)


def repository_identity(
    root: Path,
    *,
    tree_ref: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> str:
    """Return the profile-bound repository identity without inventing a Commitment."""
    profile = (
        load_committed_repository_profile(root, tree_ref, environment=environment)
        if tree_ref is not None
        else load_repository_profile(root)
    )
    return _profile_identity(profile)


def historical_repository_identity(
    root: Path,
    *,
    tree_ref: str,
    environment: Mapping[str, str] | None = None,
) -> str:
    """Read stable identity from an exact past tree without applying today's profile schema."""
    result = run_git(
        root,
        "show",
        f"{tree_ref}:.ethos/profile.toml",
        check=False,
        env=environment,
        text=False,
    )
    message = "repository_historical_identity_invalid:.ethos/profile.toml"
    if result.returncode:
        raise ValueError(message)
    return _historical_identity(result.stdout)


def repository_identities(
    root: Path,
    tree_refs: tuple[str, ...],
    *,
    environment: Mapping[str, str] | None = None,
    historical: bool = False,
    optional: frozenset[str] = frozenset(),
) -> dict[str, str]:
    """Read every selected relationship afresh, then decode each complete profile once."""
    selected = tuple(dict.fromkeys(tree_refs))
    if len(selected) <= 2 or optional:
        reader = historical_repository_identity if historical else repository_identity
        identities = {}
        for revision in selected:
            try:
                identities[revision] = reader(root, tree_ref=revision, environment=environment)
            except ValueError:
                if revision not in optional:
                    raise
        return identities
    observed = resolve_revisions(
        root,
        tuple(f"{revision}:.ethos/profile.toml" for revision in selected),
        environment=environment,
    )
    object_ids = tuple(dict.fromkeys(identity for identity in observed.values() if identity))
    payloads = dict(
        zip(object_ids, read_objects(root, object_ids, environment=environment), strict=True)
    )
    decoded: dict[str, str] = {}
    identities: dict[str, str] = {}
    for revision in selected:
        identity = observed[f"{revision}:.ethos/profile.toml"]
        if identity not in decoded:
            payload = payloads.get(identity, b"")
            decoded[identity] = (
                _historical_identity(payload)
                if historical
                else _profile_identity(
                    repository_profile_from_text(
                        root, exists=bool(identity), text=payload.decode("utf-8")
                    )
                )
            )
        identities[revision] = decoded[identity]
    return identities


def _profile_identity(profile: RepositoryProfile) -> str:
    if profile.state != "valid" or profile.declaration is None:
        raise ValueError(INVALID_PROFILE_ERROR)
    return f"repository:{profile.declaration.profile_id}"


def _historical_identity(payload: bytes) -> str:
    message = "repository_historical_identity_invalid:.ethos/profile.toml"
    try:
        values = tomllib.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ValueError(message) from error
    profile_id = values.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id:
        raise ValueError(message)
    return f"repository:{profile_id}"
