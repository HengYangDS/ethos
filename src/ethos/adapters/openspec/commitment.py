"""Resolve Commitment carriers owned by the ETHOS OpenSpec self profile."""

from __future__ import annotations

from pathlib import Path

from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.repository.openspec.identifiers import logical_change_identifier_issue
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

_CHANGES = "openspec/changes"


def openspec_profile_enabled(repo: Path, *, tree_ref: str | None = None) -> bool:
    """Return whether the explicit self-profile OpenSpec adapter is selected."""
    profile = (
        load_committed_repository_profile(repo, tree_ref)
        if tree_ref
        else load_repository_profile(repo)
    )
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    return profile.declaration is not None and profile.declaration.openspec is not None


def _paths(repo: Path, tree_ref: str | None) -> tuple[str, ...]:
    if tree_ref is not None:
        return tuple(
            path
            for path in git_stdout(
                repo, "ls-tree", "-r", "--name-only", tree_ref, "--", _CHANGES
            ).splitlines()
            if path.endswith("/commitment.toml") and "/archive/" not in path
        )
    root = repo / _CHANGES
    return tuple(
        path.relative_to(repo).as_posix()
        for path in sorted(root.glob("*/commitment.toml"))
        if path.parent.name != "archive"
    )


def resolve_openspec_commitment_carrier(
    repo: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
) -> str:
    """Select one active self-profile carrier without leaking discovery to generic code."""
    if not openspec_profile_enabled(repo, tree_ref=tree_ref):
        msg = "openspec_profile_not_enabled"
        raise ValueError(msg)
    if change_id is not None and logical_change_identifier_issue(change_id):
        message = f"openspec_active_change_identifier_invalid:{change_id}"
        raise ValueError(message)
    selected = tuple(
        path
        for path in _paths(repo, tree_ref)
        if change_id is None or Path(path).parent.name == change_id
    )
    if not selected:
        suffix = f":{change_id}" if change_id else ""
        message = f"commitment_missing{suffix}"
        raise ValueError(message)
    if len(selected) != 1:
        msg = "commitment_ambiguous"
        raise ValueError(msg)
    return selected[0]


def load_openspec_commitment(
    repo: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
    expected_digest: str | None = None,
):
    """Load the active Commitment selected by the ETHOS OpenSpec self profile."""
    carrier = resolve_openspec_commitment_carrier(repo, change_id=change_id, tree_ref=tree_ref)
    commitment = load_commitment(
        repo,
        carrier=carrier,
        tree_ref=tree_ref,
        expected_digest=expected_digest,
    )
    logical_id = Path(carrier).parent.name
    if commitment.id != f"change:{logical_id}":
        message = f"commitment_identity_mismatch:{logical_id}"
        raise ValueError(message)
    return commitment
