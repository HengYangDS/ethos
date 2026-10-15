"""Canonicalize repository-owned text projected by an OpenSpec archive."""

from __future__ import annotations

from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ethos.adapters.gates.formatting import render_source_content
from ethos.adapters.openspec.relocation import archive_relocation
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.worktree_postimage import observe_worktree_postimage

if TYPE_CHECKING:
    from collections.abc import Mapping


def archive_projection_updates(
    root: Path,
    *,
    source_head: str,
    tree: str,
    changed_paths: tuple[str, ...],
    environment: Mapping[str, str] | None = None,
) -> dict[str, bytes]:
    """Derive only permitted reference relocation for the native archive."""
    return archive_relocation(
        root,
        source_head=source_head,
        tree=tree,
        changed_paths=changed_paths,
        environment=environment,
    )[0]


def archive_projection_scope(
    root: Path,
    *,
    source_head: str,
    tree: str,
    changed_paths: tuple[str, ...],
    environment: Mapping[str, str] | None,
    allow_pending: bool,
) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """Recognize exact derived output or an unchanged input still awaiting rendering."""
    updates, preimages = archive_relocation(
        root,
        source_head=source_head,
        tree=tree,
        changed_paths=changed_paths,
        environment=environment,
    )
    pending: list[str] = []
    for path, expected in updates.items():
        actual = _blob(root, tree, path, environment)
        if actual == expected and path in changed_paths:
            continue
        if not allow_pending or actual != preimages[path]:
            return None
        pending.append(path)
    return tuple(updates), tuple(pending)


def refresh_archive_projections(root: Path, *, source_head: str) -> None:
    """Apply exact archive reference relocation without publication bindings."""
    with observe_worktree_postimage(root, previous=source_head) as observed:
        updates, preimages = archive_relocation(
            root,
            source_head=source_head,
            tree=observed.tree,
            changed_paths=observed.changed_paths,
            environment=observed.environment,
        )
    for relative, content in updates.items():
        path = root / relative
        if path.resolve() != root.resolve() / relative or path.read_bytes() not in {
            preimages[relative],
            content,
        }:
            message = f"archive_projection_preimage_changed:{relative}"
            raise ValueError(message)
        if path.read_bytes() != content:
            path.write_bytes(content)


def _blob(
    root: Path,
    tree: str,
    path: str,
    environment: Mapping[str, str] | None,
) -> bytes:
    result = run_git(root, "show", f"{tree}:{path}", check=False, text=False, env=environment)
    if result.returncode:
        message = f"archive_projection_input_unavailable:{path}"
        raise ValueError(message)
    return result.stdout


def normalize_projected_specs(root: Path, *, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Format only changed canonical specs through the shared native content owner."""
    normalized: list[str] = []
    for relative in dict.fromkeys(paths):
        path = PurePosixPath(relative)
        if not _canonical_markdown_spec(path):
            continue
        target = root.joinpath(*path.parts)
        try:
            content = target.read_bytes()
        except OSError:
            continue
        canonical, _ignored = render_source_content(
            root, relative, "prettier", content, repository_policy=False
        )
        if canonical == content:
            continue
        target.write_bytes(canonical)
        normalized.append(relative)
    return tuple(normalized)


def _canonical_markdown_spec(path: PurePosixPath) -> bool:
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and len(path.parts) >= 4
        and path.parts[:2] == ("openspec", "specs")
        and path.name == "spec.md"
    )
