"""Resolve archived intent through verified native history transformations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

from ethos.adapters.repo.commit.signature import RESULT
from ethos.adapters.repo.commit.signature import completed_signature_repair
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import validate as validate_git_effect_attestation
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from pathlib import Path


class ArchiveEdge(NamedTuple):
    """One exact object rewrite proven by an observed native effect."""

    previous: str
    current: str
    attestation_id: str
    kind: str


def resolve_archive_head(
    root: Path,
    *,
    archived_head: str,
    current_head: str,
    branch: str,
    archive_path: str,
    attestations: tuple[Any, ...],
) -> tuple[str, int, tuple[ArchiveEdge, ...]] | None:
    """Find one exact preserved archive through refresh, repair and later descendants."""
    direct = _ancestor_distance(root, archived_head, current_head)
    if direct is not None:
        return archived_head, direct, ()
    archive_tree = ref_head(root, f"{archived_head}:{archive_path}") if archive_path else ""
    if not archive_tree:
        return None
    edges = refresh_edges(root, branch=branch, attestations=attestations)
    repairs: dict[str, dict[str, object] | None] = {}
    candidates: list[tuple[str, int, tuple[ArchiveEdge, ...]]] = []
    pending: list[tuple[str, tuple[ArchiveEdge, ...], frozenset[str]]] = [
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
) -> tuple[ArchiveEdge, ...]:
    """Derive only relevant repair mappings once per resolution, never from a digest alone."""
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
                ArchiveEdge(previous, str(current), str(repair["attestation_id"]), "repair")
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


def refresh_edges(
    root: Path, *, branch: str, attestations: tuple[Any, ...]
) -> dict[str, tuple[ArchiveEdge, ...]]:
    """Derive the branch's validated adjacency relation from exact refresh evidence."""
    grouped: dict[str, list[ArchiveEdge]] = {}
    for attestation in attestations:
        edge = validated_refresh_edge(root, branch=branch, attestation=attestation)
        if edge is not None:
            grouped.setdefault(edge.previous, []).append(edge)
    return {previous: tuple(values) for previous, values in grouped.items()}


def validated_refresh_edge(
    root: Path,
    *,
    branch: str,
    attestation: Any,
) -> ArchiveEdge | None:
    """Decode one refresh edge only when both Git and native evidence validate."""
    try:
        _require(valid=attestation.predicate == "effect:git-ref-update")
        plan = plan_from_attestation(attestation)
        _require(valid=plan.policy.get("transition") == "lane.refresh")
        _require(valid=plan.policy.get("execution_branch") == branch)
        effect = git_effect_from_plan(plan)
        ref = f"refs/heads/{branch}"
        update = effect.updates.get(ref)
        _require(valid=update is not None and len(effect.updates) == 1)
        assert update is not None
        validate_git_effect_attestation(
            root,
            effect,
            attestation,
            issuer=attestation.verifier,
            plan=plan,
            current_postconditions=False,
        )
        carried = plan.prior_attestations.get("rebase")
        _require(valid=isinstance(carried, Mapping))
        rebase = Attestation.model_validate(mutable_json(carried))
        projected_body = mutable_json(rebase.payload.body)
        _require(valid=isinstance(projected_body, dict))
        assert isinstance(projected_body, dict)
        body = {str(key): value for key, value in projected_body.items()}
        before = body.get("input")
        after = body.get("output")
        freshness = body.get("freshness")
        command = body.get("command")
        repository = str(body.get("repository") or "")
        _require(valid=all(isinstance(value, dict) for value in (before, after, freshness)))
        assert isinstance(before, dict)
        assert isinstance(after, dict)
        assert isinstance(freshness, dict)
        _require(valid=isinstance(command, list | tuple) and bool(repository))
        assert isinstance(command, list | tuple)
        before_map = {str(key): value for key, value in before.items()}
        after_map = {str(key): value for key, value in after.items()}
        freshness_map = {str(key): value for key, value in freshness.items()}
        subject = freshness_map.get("subject")
        _require(valid=isinstance(subject, dict))
        assert isinstance(subject, dict)
        subject_map = {str(key): value for key, value in subject.items()}
        expected_rebase = issue_native_effect(
            root,
            effect=NativeEffect(
                predicate="effect:git-rebase",
                operation="git.rebase",
                command=tuple(str(value) for value in command),
                subject=subject_map,
                before=before_map,
                after=after_map,
            ),
            state="applied",
            commitment_digest=None,
            repository_id=repository,
            issued_at=rebase.issued_at,
        )
        candidate_heads = tuple(str(value) for value in effect.assertions.values())
        candidate_head = str(before_map.get("candidate_head") or "")
        _require(valid=rebase.canonical_json() == expected_rebase.canonical_json())
        _require(valid=repository == repository_identity(root, tree_ref=update.desired))
        _require(valid=subject_map == {"branch": branch, "candidate_head": candidate_head})
        _require(valid=before_map.get("branch") == branch)
        _require(valid=before_map.get("head") == update.expected)
        _require(valid=after_map.get("branch") == "detached")
        _require(valid=after_map.get("head") == update.desired)
        _require(valid=candidate_head == after_map.get("candidate_head"))
        _require(valid=candidate_heads == (candidate_head,))
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    return ArchiveEdge(
        previous=str(update.expected),
        current=str(update.desired),
        attestation_id=str(attestation.id),
        kind="refresh",
    )


def _require(*, valid: bool) -> None:
    if not valid:
        message = "archive_refresh_evidence_invalid"
        raise ValueError(message)
