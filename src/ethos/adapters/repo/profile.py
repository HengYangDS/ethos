"""Committed repository profile observation adapter."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import read_objects
from ethos.adapters.repo.git_object import resolve_revisions
from ethos.repository.openspec.audit import accepted_spec_root_gaps
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


def repository_identities(
    root: Path,
    tree_refs: tuple[str, ...],
    *,
    environment: Mapping[str, str] | None = None,
    historical: bool | frozenset[str] = False,
    optional: frozenset[str] = frozenset(),
) -> dict[str, str]:
    """Read every selected relationship afresh; historical revisions skip today's schema."""
    selected = tuple(dict.fromkeys(tree_refs))
    if isinstance(historical, bool):
        past = frozenset(selected) if historical else frozenset()
    else:
        past = historical
    required = tuple(revision for revision in selected if revision not in optional)
    identities = {}
    unbatched = (
        selected
        if len(required) <= 2
        else tuple(revision for revision in selected if revision in optional)
    )
    for revision in unbatched:
        reader = historical_repository_identity if revision in past else repository_identity
        try:
            identities[revision] = reader(root, tree_ref=revision, environment=environment)
        except ValueError:
            if revision not in optional:
                raise
    if len(required) <= 2:
        return identities
    observed = resolve_revisions(
        root,
        tuple(f"{revision}:.ethos/profile.toml" for revision in required),
        environment=environment,
    )
    object_ids = tuple(dict.fromkeys(identity for identity in observed.values() if identity))
    payloads = dict(
        zip(object_ids, read_objects(root, object_ids, environment=environment), strict=True)
    )
    decoded: dict[tuple[str, bool], str] = {}
    for revision in required:
        key = (observed[f"{revision}:.ethos/profile.toml"], revision in past)
        if key not in decoded:
            payload = payloads.get(key[0], b"")
            decoded[key] = (
                _historical_identity(payload)
                if key[1]
                else _profile_identity(
                    repository_profile_from_text(
                        root, exists=bool(key[0]), text=payload.decode("utf-8")
                    )
                )
            )
        identities[revision] = decoded[key]
    return {revision: identities[revision] for revision in selected if revision in identities}


def _profile_identity(profile: RepositoryProfile) -> str:
    if profile.state != "valid" or profile.declaration is None:
        raise ValueError(INVALID_PROFILE_ERROR)
    return f"repository:{profile.declaration.profile_id}"


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


class ProfilePostimage(NamedTuple):
    """One strict profile observation, identity and narrowly bound repair eligibility."""

    gap: str
    profile_id: str
    metadata_repair: bool


def profile_postimage(root: Path, postimages: Mapping[str, str | None]) -> ProfilePostimage:
    """Validate the strict profile and recognize only additive metadata binding repair."""
    text = postimages.get(".ethos/profile.toml")
    if text is None:
        return ProfilePostimage(gap="", profile_id="", metadata_repair=False)
    proposed = repository_profile_from_text(root, exists=True, text=text).declaration
    if proposed is None:
        return ProfilePostimage(gap=INVALID_PROFILE_ERROR, profile_id="", metadata_repair=False)
    current = load_repository_profile(root).declaration
    repair = False
    if (
        len(postimages) == 1
        and current is not None
        and current.openspec is not None
        and proposed.openspec is not None
    ):
        fields = ("capability_metadata", "specs_root_metadata")
        previous = {field: getattr(current.openspec, field) for field in fields}
        incoming = {field: getattr(proposed.openspec, field) for field in fields}
        restored = proposed.model_copy(
            update={"openspec": proposed.openspec.model_copy(update=previous)}
        )
        repair = (
            previous != incoming
            and all(item in incoming[field] for field in fields for item in previous[field])
            and restored == current
            and set(accepted_spec_root_gaps(root / "openspec/specs", policy=proposed.openspec))
            < set(accepted_spec_root_gaps(root / "openspec/specs", policy=current.openspec))
        )
    return ProfilePostimage("", proposed.profile_id, repair)
