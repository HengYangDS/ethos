"""Select official intent using explicit choice and native contribution provenance."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ethos.adapters.repo.commit.provenance import lane_creation_boundary
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.merge.observation import pending_merge_heads
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

if TYPE_CHECKING:
    from pathlib import Path


def requested_change(explicit: str | None = None) -> str | None:
    """Read one invocation-local intent choice without persisting permission."""
    return explicit if explicit is not None else os.environ.get("ETHOS_CHANGE")


def artifact_path_change(root: Path, paths: tuple[str, ...]) -> str | None:
    """Select one existing Change named by every path, without authorizing writes."""
    parts = [path.split("/") for path in paths]
    if not parts or any(
        len(item) < 4 or item[:2] != ["openspec", "changes"] or ".." in item for item in parts
    ):
        return None
    names = {item[2] for item in parts}
    if len(names) != 1:
        return None
    name = names.pop()
    if name == "archive" or logical_change_identifier_issue(name):
        return None
    target = root / active_change_root(name)
    return name if target.is_dir() and not target.is_symlink() else None


def resolve_change_selection(
    rows: list[dict[str, str]],
    requested: str | None,
    *,
    root: Path | None = None,
    tree_ref: str | None = None,
) -> tuple[str | None, str]:
    """Resolve one explicit or native contribution with its exact refusal."""
    names = {item["name"] for item in rows}
    if requested is not None:
        return (
            (requested, "")
            if requested in names
            else (None, f"openspec_requested_change_missing:{requested}")
        )
    if names and root is not None:
        try:
            owned = _lane_contribution(root, names, tree_ref)
        except ValueError:
            return None, "openspec_change_provenance_unresolved"
        if owned is not None:
            names = owned
            if len(owned) == 1:
                return next(iter(owned)), ""
            return None, _unselected_gap(names)
    active = [item["name"] for item in rows if item["status"] in {"in-progress", "no-tasks"}]
    if len(active) == 1:
        return active[0], ""
    return (
        (next(iter(names)), "")
        if not active and len(names) == 1
        else (None, _unselected_gap(names))
    )


def _unselected_gap(names: set[str]) -> str:
    return (
        f"openspec_active_change_ambiguous:{','.join(sorted(names))}"
        if names
        else "openspec_active_change_missing"
    )


def incoming_change_gaps(
    root: Path, selected: str, incoming: str, authored_paths: tuple[str, ...]
) -> list[str]:
    """New resolution authoring does not own other imported Change progress."""
    changes = _change_trees(root, incoming)
    if changes is None:
        return ["openspec_incoming_change_observation_unavailable"]
    bases = run_git(root, "merge-base", "--all", "HEAD", incoming, check=False, observation=True)
    base = _change_trees(root, bases.stdout.strip()) if len(bases.stdout.split()) == 1 else None
    if bases.returncode or base is None:
        return ["openspec_incoming_change_observation_unavailable"]
    return [
        f"openspec_incoming_change_modified:{name}"
        for name in sorted(changes.keys() - {selected})
        if any(path.startswith(f"{active_change_root(name)}/") for path in authored_paths)
    ]


def preserved_incoming_change_paths(
    root: Path, paths: tuple[str, ...], *, tree_ref: str
) -> tuple[str, ...]:
    """Bind a whole-Change import or removal to the exact pending native merge."""
    pending = pending_merge_heads(root)
    if len(pending) != 1:
        return ()
    incoming, staged, prior = (
        _change_trees(root, revision) for revision in (pending[0], tree_ref, "HEAD")
    )
    if incoming is None or staged is None or prior is None:
        return ()
    known = incoming.keys() | prior.keys()
    return tuple(
        path
        for path in paths
        if len(parts := path.split("/")) >= 4
        and parts[:2] == ["openspec", "changes"]
        and parts[2] in known
        and incoming.get(parts[2]) == staged.get(parts[2])
    )


def _change_trees(root: Path, revision: str) -> dict[str, str] | None:
    tree = revision
    for component in ("openspec", "changes"):
        entry = run_git(root, "ls-tree", "-z", tree, "--", component, check=False, observation=True)
        if entry.returncode:
            return None
        if not entry.stdout:
            return {}
        metadata, _name = entry.stdout.rstrip("\0").split("\t", 1)
        _mode, kind, tree = metadata.split()
        if kind != "tree":
            return None
    result = run_git(root, "ls-tree", "-z", tree, check=False, observation=True)
    if result.returncode:
        return None
    changes = {
        name: metadata.split()[2]
        for entry in result.stdout.split("\0")
        if entry
        for metadata, name in (entry.split("\t", 1),)
        if name != "archive" and metadata.split()[1] == "tree"
    }
    return None if any(logical_change_identifier_issue(name) for name in changes) else changes


def _lane_contribution(root: Path, names: set[str], tree_ref: str | None) -> set[str] | None:
    revision = tree_ref or "HEAD"
    pending = pending_merge_heads(root) if tree_ref is None else ()
    if pending:
        ours, theirs, merge = revision, pending[0], ""
        if len(pending) != 1:
            raise ValueError
    else:
        latest = run_git(
            root,
            "rev-list",
            "--first-parent",
            "--merges",
            "--max-count=1",
            revision,
            check=False,
            observation=True,
        )
        merge = latest.stdout.strip()
        if latest.returncode:
            raise ValueError
        if not merge:
            return None
        boundary = lane_creation_boundary(root, revision)
        if boundary and is_ancestor(root, merge, boundary):
            return None
        parts = run_git(
            root, "rev-list", "--parents", "-n", "1", merge, observation=True
        ).stdout.split()
        ours, theirs = (parts[1], parts[2]) if len(parts) == 3 else ("", "")
    return _owned_changes(root, names, revision, ours, theirs, merge)


def _owned_changes(
    root: Path, names: set[str], revision: str, ours: str, theirs: str, merge: str
) -> set[str]:
    if not ours or not theirs:
        raise ValueError
    bases = run_git(root, "merge-base", "--all", ours, theirs, check=False, observation=True)
    if bases.returncode or len(bases.stdout.split()) != 1:
        raise ValueError
    base, own, incoming = (_change_trees(root, ref) for ref in (bases.stdout.strip(), ours, theirs))
    if base is None or own is None or incoming is None:
        raise ValueError
    owned = {name for name in names if name in own and own[name] != base.get(name)}
    contributed = {name for name in names if name in incoming and incoming[name] != base.get(name)}
    if owned & contributed:
        raise ValueError
    if merge:
        merged, current = _change_trees(root, merge), _change_trees(root, revision)
        if merged is None or current is None:
            raise ValueError
        owned |= {name for name in names if name in current and current[name] != merged.get(name)}
        owned |= names - current.keys()
    else:
        owned |= names - own.keys() - incoming.keys()
    return owned
