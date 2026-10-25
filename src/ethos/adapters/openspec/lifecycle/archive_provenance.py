"""Resolve archived intent through verified native history transformations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.repo.commit.history import observe_history_repair_mapping
from ethos.adapters.repo.commit.rewrite import RewriteEdge
from ethos.adapters.repo.commit.rewrite import refresh_edges
from ethos.adapters.repo.commit.signature import RESULT
from ethos.adapters.repo.commit.signature import completed_signature_repair
from ethos.adapters.repo.git import is_ancestor
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
    repair_mappings: dict[str, dict[str, str]] | None = None,
) -> tuple[str, int, tuple[RewriteEdge, ...]] | None:
    """Find one exact preserved archive through refresh, repair and later descendants."""
    direct = _ancestor_distance(root, archived_head, current_head)
    if direct is not None:
        return archived_head, direct, ()
    archive_tree = ref_head(root, f"{archived_head}:{archive_path}") if archive_path else ""
    if not archive_tree:
        return None
    repair_mappings = {} if repair_mappings is None else repair_mappings
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
                *refresh_edges(root, branch=branch, attestations=attestations, previous=commit).get(
                    commit, ()
                ),
                *_repair_edges(root, commit, attestations, repairs, repair_mappings),
            )
            if edge.current not in seen
        )
        if len(next_edges) > 1:
            next_edges = tuple(
                verified[0]
                for edge in next_edges
                if (verified := _verified_chain(root, (edge,), attestations, repairs)) is not None
            )
            if len(next_edges) > 1:
                return None
        pending.extend((edge.current, (*chain, edge), seen | {edge.current}) for edge in next_edges)
    for nearest in sorted({candidate[1] for candidate in candidates}):
        selected = [
            (commit, distance, verified)
            for commit, distance, chain in candidates
            if distance == nearest
            and (verified := _verified_chain(root, chain, attestations, repairs)) is not None
        ]
        if selected:
            return selected[0] if len(selected) == 1 else None
    return None


def _verified_chain(
    root: Path,
    chain: tuple[RewriteEdge, ...],
    attestations: tuple[Any, ...],
    repairs: dict[str, dict[str, object] | None],
) -> tuple[RewriteEdge, ...] | None:
    """Demand full fresh repair trust only for a path that can reach current history."""
    verified = []
    for edge in chain:
        if edge.kind != "repair":
            verified.append(edge)
            continue
        if edge.candidate not in repairs:
            repairs[edge.candidate] = completed_signature_repair(
                root, new=edge.candidate, attestations=attestations
            )
        repair = repairs[edge.candidate]
        mapping = repair.get("mapping") if repair else None
        if not isinstance(mapping, Mapping) or mapping.get(edge.previous) != edge.current:
            return None
        assert repair is not None
        verified.append(edge._replace(attestation_id=str(repair["attestation_id"])))
    return tuple(verified)


def _repair_edges(
    root: Path,
    previous: str,
    attestations: tuple[Any, ...],
    cache: dict[str, dict[str, object] | None],
    repair_mappings: dict[str, dict[str, str]],
) -> tuple[RewriteEdge, ...]:
    """Observe possible repair edges without treating payload conservation as trust."""
    edges = []
    for attestation in attestations:
        if attestation.predicate != RESULT or not (
            new := str(attestation.payload.body.get("replacement") or "")
        ):
            continue
        body = attestation.payload.body
        coordinates = body.get("coordinates")
        old = str(coordinates.get("old") or "") if isinstance(coordinates, Mapping) else ""
        if new not in cache:
            if new not in repair_mappings:
                history = coordinates.get("history") if isinstance(coordinates, Mapping) else None
                if isinstance(history, Mapping) and isinstance(
                    corrections := history.get("corrections"), Mapping
                ):
                    if not is_ancestor(root, previous, old) or not any(
                        is_ancestor(root, str(oid), previous) for oid in corrections
                    ):
                        continue
                    repair_mappings[new] = observe_history_repair_mapping(
                        root, old, new, corrections=corrections
                    )
                else:
                    if previous != old:
                        continue
                    repair_mappings[new] = {old: new}
            mapping = repair_mappings[new]
        else:
            repair = cache[new]
            if repair is None:
                continue
            mapping = repair["mapping"]
            assert isinstance(mapping, dict)
        if current := mapping.get(previous):
            edges.append(RewriteEdge(previous, str(current), attestation.id, "repair", new))
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
