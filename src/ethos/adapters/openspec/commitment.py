"""Resolve Commitment carriers owned by the ETHOS OpenSpec self profile."""

from __future__ import annotations

from pathlib import Path

from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.git import git_stdout
from ethos.repository.context import is_product_root
from ethos.repository.openspec.audit import tasks_complete
from ethos.repository.openspec.identifiers import logical_change_identifier_issue
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

_CHANGES = "openspec/changes"


def openspec_profile_enabled(repo: Path, *, tree_ref: str | None = None) -> bool:
    """Return whether the explicit self-profile OpenSpec adapter is selected."""
    if is_product_root(repo):
        return True
    profile = load_repository_profile(repo, tree_ref=tree_ref)
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


def _all_paths(repo: Path, tree_ref: str | None) -> tuple[str, ...]:
    """Return active and archived Commitment paths inside the OpenSpec adapter."""
    if tree_ref is not None:
        return tuple(
            path
            for path in git_stdout(
                repo, "ls-tree", "-r", "--name-only", tree_ref, "--", _CHANGES
            ).splitlines()
            if path.endswith("/commitment.toml")
        )
    root = repo / _CHANGES
    return tuple(
        path.relative_to(repo).as_posix() for path in sorted(root.rglob("commitment.toml"))
    )


def _text(repo: Path, relative: str, tree_ref: str | None) -> str:
    if tree_ref is None:
        try:
            return (repo / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return ""
    return git_stdout(repo, "show", f"{tree_ref}:{relative}")


def _active(repo: Path, relative: str, tree_ref: str | None) -> bool:
    tasks = relative.removesuffix("commitment.toml") + "tasks.md"
    text = _text(repo, tasks, tree_ref)
    return not text or not tasks_complete(text)


def resolve_openspec_commitment_carrier(
    repo: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
) -> str:
    """Select one active self-profile carrier without leaking discovery to generic code."""
    if not openspec_profile_enabled(repo, tree_ref=tree_ref):
        raise ValueError("openspec_profile_not_enabled")
    if change_id is not None and logical_change_identifier_issue(change_id):
        message = f"openspec_active_change_identifier_invalid:{change_id}"
        raise ValueError(message)
    selected = tuple(
        path
        for path in _paths(repo, tree_ref)
        if _active(repo, path, tree_ref)
        and (change_id is None or Path(path).parent.name == change_id)
    )
    if not selected:
        if change_id is not None:
            candidate = f"{_CHANGES}/{change_id}/commitment.toml"
            if candidate in _paths(repo, tree_ref) and not _active(repo, candidate, tree_ref):
                message = f"commitment_complete:{change_id}"
                raise ValueError(message)
        suffix = f":{change_id}" if change_id else ""
        message = f"commitment_missing{suffix}"
        raise ValueError(message)
    if len(selected) != 1:
        raise ValueError("commitment_ambiguous")
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


def load_lease_bound_openspec_commitment(
    repo: Path,
    *,
    expected_head: str,
    base_commitment_digest: str,
    change_id: str | None = None,
):
    """Load the self-profile carrier named by one lease-bound tree."""
    if not base_commitment_digest:
        raise ValueError("lease_base_commitment_digest_missing")
    matches = tuple(
        commitment
        for carrier in _all_paths(repo, expected_head)
        if (
            commitment := load_commitment(
                repo,
                carrier=carrier,
                tree_ref=expected_head,
            )
        ).digest()
        == base_commitment_digest
    )
    if len(matches) != 1:
        raise ValueError("lease_base_commitment_digest_mismatch")
    commitment = matches[0]
    if change_id is not None and commitment.id != f"change:{change_id}":
        message = f"commitment_missing:{change_id}"
        raise ValueError(message)
    return commitment
