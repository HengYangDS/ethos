"""Load profile-selected Commitment carriers without format-specific discovery."""

from __future__ import annotations

import tomllib
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import committed_file_text
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import load_commitment_file
from ethos.normalization.coercion import object_sequence
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from collections.abc import Mapping

_REPOSITORY_COMMITMENT = ".ethos/commitment.toml"
_TUPLE_FIELDS = {
    "subjects",
    "scope",
    "invariants",
    "acceptance",
    "risks",
    "authority_refs",
    "permissions",
    "hypotheses",
    "dependencies",
}


def _relative_carrier(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or value.startswith(("/", "./"))
        or "\\" in value
        or "\x00" in value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError("commitment_carrier_invalid")
    return value


def _normalized(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        key: tuple(value) if key in _TUPLE_FIELDS and isinstance(value, list) else value
        for key, value in payload.items()
    }


def _load(
    repo: Path,
    relative: str,
    *,
    tree_ref: str | None = None,
    repository_id: str = "",
) -> Commitment:
    try:
        if tree_ref is None:
            return load_commitment_file(repo / relative, repository_id=repository_id)
        text = committed_file_text(repo, tree_ref, relative)
        if not text:
            raise FileNotFoundError(relative)
        payload = _normalized(tomllib.loads(text))
        if repository_id:
            payload["subjects"] = tuple(
                repository_id if subject == "repository:self" else str(subject)
                for subject in object_sequence(payload.get("subjects"))
            )
        return Commitment.model_validate(payload)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, TypeError, ValueError) as exc:
        message = f"commitment_invalid:{relative}"
        raise ValueError(message) from exc


def load_repository_commitment(repo: Path, *, tree_ref: str | None = None) -> Commitment:
    """Load the stable repository identity Commitment."""
    try:
        commitment = _load(repo, _REPOSITORY_COMMITMENT, tree_ref=tree_ref)
    except ValueError as exc:
        message = f"repository_commitment_missing:{_REPOSITORY_COMMITMENT}"
        raise ValueError(message) from exc
    if commitment.subjects != (commitment.id,) or not commitment.id.startswith("repository:"):
        raise ValueError("repository_commitment_identity_mismatch")
    return commitment


def _selected_carrier(repo: Path, *, tree_ref: str | None, carrier: str | None) -> str:
    if carrier is not None:
        return _relative_carrier(carrier)
    profile = load_repository_profile(repo, tree_ref=tree_ref)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    return (
        profile.declaration.commitment
        if profile.declaration is not None
        else _REPOSITORY_COMMITMENT
    )


def load_commitment(
    repo: Path,
    *,
    carrier: str | None = None,
    change_id: str | None = None,
    tree_ref: str | None = None,
    expected_digest: str | None = None,
) -> Commitment:
    """Load one explicit or profile-selected Commitment carrier.

    ``change_id`` constrains the selected Commitment identity; it never triggers
    directory discovery. Format-specific selectors belong to their adapters.
    """
    relative = _selected_carrier(repo, tree_ref=tree_ref, carrier=carrier)
    repository = load_repository_commitment(repo, tree_ref=tree_ref)
    commitment = (
        repository
        if relative == _REPOSITORY_COMMITMENT
        else _load(repo, relative, tree_ref=tree_ref, repository_id=repository.id)
    )
    if change_id is not None and commitment.id != f"change:{change_id}":
        message = f"commitment_missing:{change_id}"
        raise ValueError(message)
    if expected_digest is not None and commitment.digest() != expected_digest:
        raise ValueError("commitment_digest_mismatch")
    return commitment


def load_lease_bound_commitment(
    repo: Path,
    *,
    expected_head: str,
    base_commitment_digest: str,
    carrier: str | None = None,
    change_id: str | None = None,
) -> Commitment:
    """Load one carrier from the lease-bound tree and require its exact digest."""
    if not base_commitment_digest:
        raise ValueError("lease_base_commitment_digest_missing")
    try:
        return load_commitment(
            repo,
            carrier=carrier,
            change_id=change_id,
            tree_ref=expected_head,
            expected_digest=base_commitment_digest,
        )
    except ValueError as exc:
        if str(exc) != "commitment_digest_mismatch":
            raise
        raise ValueError("lease_base_commitment_digest_mismatch") from exc
