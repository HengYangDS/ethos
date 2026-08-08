"""Load profile-selected Commitment carriers without format-specific discovery."""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import committed_file_bytes
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import exact_rename_target
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.profile import load_committed_repository_profile
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
        msg = "commitment_carrier_invalid"
        raise ValueError(msg)
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
    environment: dict[str, str] | None = None,
) -> Commitment:
    try:
        if tree_ref is None:
            return load_commitment_file(repo / relative, repository_id=repository_id)
        raw = committed_file_bytes(repo, tree_ref, relative, environment=environment)
        if not raw:
            raise FileNotFoundError(relative)
        text = raw.decode("utf-8")
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


def load_repository_commitment(
    repo: Path,
    *,
    tree_ref: str | None = None,
    environment: dict[str, str] | None = None,
) -> Commitment:
    """Load the stable repository identity Commitment."""
    try:
        commitment = _load(
            repo,
            _REPOSITORY_COMMITMENT,
            tree_ref=tree_ref,
            environment=environment,
        )
    except ValueError as exc:
        message = f"repository_commitment_missing:{_REPOSITORY_COMMITMENT}"
        raise ValueError(message) from exc
    if commitment.subjects != (commitment.id,) or not commitment.id.startswith("repository:"):
        msg = "repository_commitment_identity_mismatch"
        raise ValueError(msg)
    return commitment


def _selected_carrier(repo: Path, *, tree_ref: str | None, carrier: str | None) -> str:
    if carrier is not None:
        return _relative_carrier(carrier)
    profile = (
        load_committed_repository_profile(repo, tree_ref)
        if tree_ref
        else load_repository_profile(repo)
    )
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
    environment: dict[str, str] | None = None,
) -> Commitment:
    """Load one explicit or profile-selected Commitment carrier.

    ``change_id`` constrains the selected Commitment identity; it never triggers
    directory discovery. Format-specific selectors belong to their adapters.
    """
    relative = _selected_carrier(repo, tree_ref=tree_ref, carrier=carrier)
    repository = load_repository_commitment(
        repo,
        tree_ref=tree_ref,
        environment=environment,
    )
    commitment = (
        repository
        if relative == _REPOSITORY_COMMITMENT
        else _load(
            repo,
            relative,
            tree_ref=tree_ref,
            repository_id=repository.id,
            environment=environment,
        )
    )
    if change_id is not None and commitment.id != f"change:{change_id}":
        message = f"commitment_missing:{change_id}"
        raise ValueError(message)
    if expected_digest is not None and commitment.digest() != expected_digest:
        msg = "commitment_digest_mismatch"
        raise ValueError(msg)
    return commitment


def exact_commitment_fields(
    repo: Path,
    *,
    head: str,
    carrier: str,
    change_id: str | None = None,
    environment: dict[str, str] | None = None,
) -> dict[str, str]:
    """Describe one committed carrier by its exact Git and semantic coordinates."""
    try:
        relative = _relative_carrier(carrier)
    except ValueError as exc:
        message = "commitment_carrier_path_invalid"
        raise ValueError(message) from exc
    tree = current_tree(repo, head, environment=environment)
    if not tree:
        message = "commitment_head_unreadable"
        raise ValueError(message)
    raw = committed_file_bytes(repo, tree, relative, environment=environment)
    if not raw:
        message = "commitment_carrier_missing"
        raise ValueError(message)
    return {
        "expected_head": head,
        "expected_tree": tree,
        "base_commitment_path": relative,
        "base_commitment_bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "base_commitment_digest": load_commitment(
            repo,
            carrier=relative,
            change_id=change_id,
            tree_ref=tree,
            environment=environment,
        ).digest(),
    }


def relocated_commitment_fields(
    repo: Path,
    *,
    old_head: str,
    new_head: str,
    lease: Mapping[str, object],
) -> dict[str, str]:
    """Resolve one Commitment target moved by one exact Git rename."""
    source = str(lease.get("base_commitment_path") or "")
    target = exact_rename_target(repo, old_head, new_head, source)
    if not target:
        message = "lease_base_commitment_path_mismatch"
        raise ValueError(message)
    return exact_commitment_fields(repo, head=new_head, carrier=target)


def relocated_commitment_fields_to(
    repo: Path,
    *,
    old_head: str,
    new_head: str,
    lease: Mapping[str, object],
    carrier: str,
) -> dict[str, str]:
    """Validate one exact semantic relocation to a predeclared carrier path."""
    source_commitment = load_lease_bound_commitment(repo, lease=lease)
    target = exact_commitment_fields(
        repo,
        head=new_head,
        carrier=carrier,
        change_id=source_commitment.id.removeprefix("change:"),
    )
    parents = run_git(repo, "rev-list", "--parents", "-n", "1", new_head).stdout.split()
    if (
        parents != [new_head, old_head]
        or target["base_commitment_digest"] != source_commitment.digest()
    ):
        message = "lease_base_commitment_path_mismatch"
        raise ValueError(message)
    return target


def load_lease_bound_commitment(
    repo: Path,
    *,
    lease: Mapping[str, object],
    change_id: str | None = None,
    environment: dict[str, str] | None = None,
) -> Commitment:
    """Load one exact tree-bound carrier without discovery or working-tree reads."""
    expected = {
        name: str(lease.get(name) or "")
        for name in (
            "expected_head",
            "expected_tree",
            "base_commitment_path",
            "base_commitment_bytes_sha256",
            "base_commitment_digest",
        )
    }
    missing = next((name for name, value in expected.items() if not value), "")
    if missing:
        message = f"lease_{missing}_missing"
        raise ValueError(message)
    try:
        actual = exact_commitment_fields(
            repo,
            head=expected["expected_head"],
            carrier=expected["base_commitment_path"],
            change_id=change_id,
            environment=environment,
        )
    except ValueError as exc:
        mapped = {
            "commitment_carrier_path_invalid": "lease_base_commitment_path_mismatch",
            "commitment_carrier_missing": "lease_base_commitment_path_mismatch",
            "commitment_head_unreadable": "lease_expected_tree_mismatch",
        }.get(str(exc))
        if mapped:
            raise ValueError(mapped) from exc
        message = "lease_base_commitment_digest_mismatch"
        raise ValueError(message) from exc
    mismatch = next((name for name in expected if actual[name] != expected[name]), "")
    if mismatch:
        raise ValueError(
            {
                "expected_tree": "lease_expected_tree_mismatch",
                "base_commitment_path": "lease_base_commitment_path_mismatch",
                "base_commitment_bytes_sha256": "lease_base_commitment_bytes_mismatch",
                "base_commitment_digest": "lease_base_commitment_digest_mismatch",
            }.get(mismatch, "lease_head_stale")
        )
    try:
        return load_commitment(
            repo,
            carrier=actual["base_commitment_path"],
            change_id=change_id,
            tree_ref=actual["expected_tree"],
            environment=environment,
        )
    except ValueError as exc:
        message = "lease_base_commitment_digest_mismatch"
        raise ValueError(message) from exc
