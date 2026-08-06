"""Admit an exact staged overlay into the next Change generation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TypedDict

from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.git import git_stdout
from ethos.normalization.coercion import repository_path_matches

if TYPE_CHECKING:
    from pathlib import Path


class ChangeOverlay(TypedDict):
    """Exact pre-transition overlay observation."""

    paths: tuple[str, ...]
    digest: str
    required_gaps: list[str]


def change_overlay_report(
    root: Path,
    *,
    scope: tuple[str, ...],
    expected_digest: str,
    apply: bool,
) -> ChangeOverlay:
    """Bind a clean tree or one fully staged, scope-covered overlay."""
    paths = changed_paths(root)
    if not paths:
        return {"paths": (), "digest": "", "required_gaps": []}
    unstaged = tuple(git_stdout(root, "diff", "--name-only", "--").splitlines())
    staged = tuple(git_stdout(root, "diff", "--cached", "--name-only", "--").splitlines())
    digest = dirty_content_sha256(root)
    gaps: list[str] = []
    if unstaged or set(staged) != set(paths):
        gaps.append("openspec_change_overlay_not_fully_staged")
    uncovered = [
        path
        for path in paths
        if not any(repository_path_matches(path, pattern) for pattern in scope)
    ]
    gaps.extend(f"openspec_change_overlay_uncovered:{path}" for path in uncovered)
    if expected_digest and expected_digest != digest:
        gaps.append("openspec_change_overlay_digest_mismatch")
    if apply and not expected_digest:
        gaps.append("openspec_change_overlay_digest_required")
    return {"paths": paths, "digest": digest, "required_gaps": gaps}
