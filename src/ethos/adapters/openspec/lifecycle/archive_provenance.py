"""Resolve archived intent through verified native history transformations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.repo.commit.rewrite import RewriteEdge
from ethos.adapters.repo.commit.rewrite import refresh_edges
from ethos.adapters.repo.commit.signature import RESULT
from ethos.adapters.repo.commit.signature import completed_signature_repair
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from pathlib import Path


def resolve_archive_head(
    root: Path,
    *,
    archived_head: str,
    current_head: str,
    branch: str,
    archive_path: str,
    attestations: tuple[Any, ...],
    repairs: dict[str, dict[str, object] | None],
) -> tuple[str, int, tuple[RewriteEdge, ...]] | None:
    """Find one exact preserved archive through refresh, repair and later descendants."""
    direct = _ancestor_distance(root, archived_head, current_head)
    if direct is not None:
        return archived_head, direct, ()
    archive_tree = ref_head(root, f"{archived_head}:{archive_path}") if archive_path else ""
    if not archive_tree:
        return None
    edges = refresh_edges(root, branch=branch, attestations=attestations)
    candidates: list[tuple[str, int, tuple[RewriteEdge, ...]]] = []
    pending: list[tuple[str, tuple[RewriteEdge, ...], frozenset[str]]] = [
        (archived_head, (), frozenset({archived_head}))
    ]
    while pending:
        commit, chain, seen = pending.pop()
        if ref_head(root, f"{commit}:{archive_path}") != archive_tree:
            continue
        distance = _ancestor_distance(root, commit, current_head)
        if distance is not None:
            candidates.append((commit, distance, chain))
        next_edges = tuple(
            edge
            for edge in (
                *edges.get(commit, ()),
                *_repair_edges(root, commit, attestations, repairs),
            )
            if edge.current not in seen
        )
        if len(next_edges) > 1:
            return None
        pending.extend((edge.current, (*chain, edge), seen | {edge.current}) for edge in next_edges)
    if not candidates:
        return None
    nearest = min(candidate[1] for candidate in candidates)
    selected = [candidate for candidate in candidates if candidate[1] == nearest]
    return selected[0] if len(selected) == 1 else None


def _repair_edges(
    root: Path,
    previous: str,
    attestations: tuple[Any, ...],
    cache: dict[str, dict[str, object] | None],
) -> tuple[RewriteEdge, ...]:
    """Verify each relevant repair once in this observation, never from a digest alone."""
    edges = []
    for attestation in attestations:
        if attestation.predicate != RESULT:
            continue
        body = attestation.payload.body
        coordinates = body.get("coordinates")
        old = str(coordinates.get("old") or "") if isinstance(coordinates, Mapping) else ""
        new = str(body.get("replacement") or "")
        if not new or _ancestor_distance(root, previous, old) is None:
            continue
        if new not in cache:
            cache[new] = completed_signature_repair(root, new=new, attestations=attestations)
        repair = cache[new]
        if repair is None:
            continue
        mapping = repair["mapping"]
        assert isinstance(mapping, dict)
        if current := mapping.get(previous):
            edges.append(
                RewriteEdge(previous, str(current), str(repair["attestation_id"]), "repair")
            )
    return tuple(edges)


def _ancestor_distance(root: Path, ancestor: str, descendant: str) -> int | None:
    """Return native Git distance; failed or malformed observations never invent ancestry."""
    if not ancestor or not descendant:
        return None
    if run_git(
        root, "merge-base", "--is-ancestor", ancestor, descendant, check=False, observation=True
    ).returncode:
        return None
    result = run_git(
        root, "rev-list", "--count", f"{ancestor}..{descendant}", check=False, observation=True
    )
    try:
        return int(result.stdout.strip()) if result.returncode == 0 else None
    except ValueError:
        return None
