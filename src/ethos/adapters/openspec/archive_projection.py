"""Canonicalize repository-owned text projected by an OpenSpec archive."""

from __future__ import annotations

from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ethos.adapters.openspec.relocation import archive_relocation
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.worktree_postimage import observe_worktree_postimage
from ethos.repository.policy.projections import SOURCE_BINDING_DECLARATION
from ethos.repository.policy.projections import render_source_bindings
from ethos.repository.policy.projections import source_binding_inputs

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
    """Derive the archive's binding closure from the trusted source declaration."""
    return _archive_projection_values(
        root,
        source_head,
        tree,
        changed_paths,
        environment,
        _binding_declaration(root, source_head, environment),
    )[0]


def _archive_projection_values(
    root: Path,
    source_head: str,
    tree: str,
    changed_paths: tuple[str, ...],
    environment: Mapping[str, str] | None,
    declaration: bytes | None,
) -> tuple[dict[str, bytes], dict[str, bytes]]:
    updates, preimages = archive_relocation(
        root,
        source_head=source_head,
        tree=tree,
        changed_paths=changed_paths,
        environment=environment,
    )
    if declaration is not None:
        projected = _projection_updates(
            root, source_head, tree, changed_paths, environment, declaration, updates
        )
        preimages.update({path: _blob(root, source_head, path, environment) for path in projected})
        updates.update(projected)
    return updates, preimages


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
    updates, preimages = _archive_projection_values(
        root,
        source_head,
        tree,
        changed_paths,
        environment,
        _binding_declaration(root, source_head, environment),
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


def _projection_updates(
    root: Path,
    source_head: str,
    tree: str,
    changed_paths: tuple[str, ...],
    environment: Mapping[str, str] | None,
    declaration: bytes,
    relocated: Mapping[str, bytes],
) -> dict[str, bytes]:
    if _blob(root, tree, SOURCE_BINDING_DECLARATION, environment) != declaration:
        message = "archive_projection_declaration_changed"
        raise ValueError(message)
    output, bindings = source_binding_inputs(declaration)
    sources = {binding["path"] for binding in bindings.values()}
    affected = sources.intersection(changed_paths)
    if not affected:
        return {}
    if any(not _canonical_markdown_spec(PurePosixPath(path)) for path in affected):
        message = "archive_projection_input_outside_effect"
        raise ValueError(message)
    before = {path: _blob(root, source_head, path, environment) for path in sources}
    after = {
        path: relocated[path] if path in relocated else _blob(root, tree, path, environment)
        for path in sources
    }
    graph = _blob(root, source_head, output, environment)
    updated = render_source_bindings(graph, bindings, before, after)
    return {output: updated} if updated != graph else {}


def refresh_archive_projections(root: Path, *, source_head: str) -> None:
    """Apply only deterministic bindings to unchanged authored projection files."""
    declaration = _binding_declaration(root, source_head, None)
    with observe_worktree_postimage(root, previous=source_head) as observed:
        updates, preimages = _archive_projection_values(
            root,
            source_head,
            observed.tree,
            observed.changed_paths,
            observed.environment,
            declaration,
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


def _binding_declaration(
    root: Path,
    head: str,
    environment: Mapping[str, str] | None,
) -> bytes | None:
    declared = run_git(
        root,
        "ls-tree",
        head,
        "--",
        SOURCE_BINDING_DECLARATION,
        check=False,
        env=environment,
    )
    if declared.returncode:
        message = "archive_projection_declaration_unavailable"
        raise ValueError(message)
    return _blob(root, head, SOURCE_BINDING_DECLARATION, environment) if declared.stdout else None


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
    """Give changed canonical Markdown specs exactly one terminal newline."""
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
        canonical = content.rstrip(b"\n") + b"\n"
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
