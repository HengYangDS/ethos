"""Recognize the official OpenSpec Change-to-archive transition."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

from ethos.adapters.openspec.lifecycle.archive_binding import archive_root_from_path
from ethos.adapters.openspec.lifecycle.archive_binding import archived_change_from_path
from ethos.adapters.openspec.lifecycle.archive_binding import collision_preservation_path
from ethos.adapters.openspec.lifecycle.archive_refresh import RefreshEdge
from ethos.adapters.openspec.lifecycle.archive_refresh import validated_refresh_edge
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import validate as validate_git_effect_attestation
from ethos.adapters.repo.worktree_postimage import observe_worktree_postimage
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Commitment
from ethos.normalization.coercion import repository_path_matches
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path


class ArchivePostimage(NamedTuple):
    """One exact official archive post-image observed from the worktree."""

    change: str
    head: str
    scope: Mapping[str, object] | None
    active_present: bool


class AttestedArchive(NamedTuple):
    """One validated archive effect and its distance from the current HEAD."""

    distance: int
    commitment: Commitment
    authority: dict[str, object]


def attested_archive_transition(
    root: Path,
    *,
    head: str,
    change: str | None = None,
) -> tuple[Commitment, dict[str, object]] | None:
    """Recover archived intent only from its exact Git-effect Attestation."""
    try:
        _identity, attestations = read_attestation_set(root)
    except ValueError:
        return None
    matches: list[AttestedArchive] = []
    for attestation in attestations:
        match = _attested_archive(
            root,
            head=head,
            change=change,
            attestation=attestation,
            attestations=attestations,
        )
        if match is not None:
            matches.append(match)
    if not matches:
        return None
    nearest = min(match.distance for match in matches)
    selected = [match for match in matches if match.distance == nearest]
    if len(selected) > 1:
        msg = "openspec_archive_attestation_ambiguous"
        raise ValueError(msg)
    match = selected[0]
    return match.commitment, match.authority


def _attested_archive(
    root: Path,
    *,
    head: str,
    change: str | None,
    attestation: Any,
    attestations: tuple[Any, ...],
) -> AttestedArchive | None:
    """Validate one archive effect as a current-history intent source."""
    if attestation.predicate != "effect:git-ref-update":
        return None
    try:
        plan = plan_from_attestation(attestation)
        effect = git_effect_from_plan(plan)
        archived_change = str(plan.policy.get("change") or "")
        branch = str(plan.policy.get("branch") or "")
        update = effect.updates.get(f"refs/heads/{branch}")
        desired = str(update.desired) if update is not None else ""
        values = plan.facts.get("values")
        facts = values if isinstance(values, Mapping) else {}
        paths = tuple(str(path) for path in facts.get("changed_paths", ()))
        archive_path = str(facts.get("archive_path") or "")
        resolved = _resolve_archive_head(
            root,
            archived_head=desired,
            current_head=head,
            branch=branch,
            archive_path=archive_path,
            attestations=attestations,
        )
        if (
            plan.policy.get("transition") != "openspec.archive"
            or not archived_change
            or not branch
            or update is None
            or (change is not None and archived_change != change)
            or plan.commitment is None
            or resolved is None
            or current_tree(root, desired) == ""
            or not paths
        ):
            return None
        validate_git_effect_attestation(
            root,
            effect,
            attestation,
            issuer=attestation.verifier,
            plan=plan,
            current_postconditions=False,
        )
        commitment = Commitment.model_validate(dict(plan.commitment))
    except (TypeError, ValueError):
        return None
    resolved_head, distance, refresh_attestation_ids = resolved
    return AttestedArchive(
        distance,
        commitment,
        {
            "predicate": "effect:git-ref-update",
            "attestation_id": attestation.id,
            "effect_digest": str(attestation.effect_digest or ""),
            "plan_digest": plan.digest,
            "claim": {
                "operation": "openspec.archive",
                "effect": str(attestation.effect_digest or ""),
            },
            "source": "archive_commit",
            "resolved_head": resolved_head,
            "refresh_attestation_ids": list(refresh_attestation_ids),
            "authorized_paths": list(paths),
        },
    )


def _resolve_archive_head(
    root: Path,
    *,
    archived_head: str,
    current_head: str,
    branch: str,
    archive_path: str,
    attestations: tuple[Any, ...],
) -> tuple[str, int, tuple[str, ...]] | None:
    """Resolve one archive commit through an exact, unambiguous refresh chain."""
    direct_distance = _ancestor_distance(root, archived_head, current_head)
    if direct_distance is not None:
        return archived_head, direct_distance, ()
    if not archive_path:
        return None
    archive_tree = _object_id(root, f"{archived_head}:{archive_path}")
    if not archive_tree:
        return None
    edges = _refresh_edges(root, branch=branch, attestations=attestations)
    candidates, graph_ambiguous = _archive_refresh_candidates(
        root,
        archived_head=archived_head,
        current_head=current_head,
        archive_path=archive_path,
        archive_tree=archive_tree,
        edges=edges,
    )
    if not candidates or graph_ambiguous:
        return None
    nearest = min(candidate[1] for candidate in candidates)
    selected = [candidate for candidate in candidates if candidate[1] == nearest]
    return selected[0] if len(selected) == 1 else None


def _refresh_edges(
    root: Path,
    *,
    branch: str,
    attestations: tuple[Any, ...],
) -> dict[str, tuple[RefreshEdge, ...]]:
    grouped: dict[str, list[RefreshEdge]] = {}
    for attestation in attestations:
        edge = validated_refresh_edge(root, branch=branch, attestation=attestation)
        if edge is not None:
            grouped.setdefault(edge.previous, []).append(edge)
    return {previous: tuple(values) for previous, values in grouped.items()}


def _archive_refresh_candidates(
    root: Path,
    *,
    archived_head: str,
    current_head: str,
    archive_path: str,
    archive_tree: str,
    edges: Mapping[str, tuple[RefreshEdge, ...]],
) -> tuple[list[tuple[str, int, tuple[str, ...]]], bool]:
    candidates: list[tuple[str, int, tuple[str, ...]]] = []
    ambiguous = False
    pending: list[tuple[str, tuple[str, ...], frozenset[str]]] = [
        (archived_head, (), frozenset({archived_head}))
    ]
    while pending:
        commit, chain, seen = pending.pop()
        distance = _ancestor_distance(root, commit, current_head)
        same_archive = _object_id(root, f"{commit}:{archive_path}") == archive_tree
        if not same_archive:
            continue
        if distance is not None:
            candidates.append((commit, distance, chain))
        next_edges = tuple(edge for edge in edges.get(commit, ()) if edge.current not in seen)
        if len(next_edges) > 1:
            ambiguous = True
        pending.extend(
            (edge.current, (*chain, edge.attestation_id), seen | {edge.current})
            for edge in next_edges
        )
    return candidates, ambiguous


def _ancestor_distance(root: Path, ancestor: str, descendant: str) -> int | None:
    """Return the exact Git distance when the archive effect remains in history."""
    if not ancestor or not descendant:
        return None
    if (
        run_git(
            root,
            "merge-base",
            "--is-ancestor",
            ancestor,
            descendant,
            check=False,
            observation=True,
        ).returncode
        != 0
    ):
        return None
    result = run_git(
        root,
        "rev-list",
        "--count",
        f"{ancestor}..{descendant}",
        check=False,
        observation=True,
    )
    try:
        return int(result.stdout.strip()) if result.returncode == 0 else None
    except ValueError:
        return None


def archive_postimage(root: Path, *, head: str, change: str) -> ArchivePostimage | None:
    """Observe one exact official archive post-image without minting authority."""
    if not change:
        return None
    active = active_change_root(change)
    with observe_worktree_postimage(root, previous=head) as observed:
        active_present = (
            _object_id(
                root,
                f"{observed.tree}:{active}",
                environment=observed.environment,
            )
            != ""
        )
        if observed.tree == current_tree(root, head):
            return ArchivePostimage(change, head, None, active_present)
        scope = archive_postimage_scope_report(
            root,
            changed_paths=observed.changed_paths,
            requested_change=change,
            tree=observed.tree,
            source_head=head,
            environment=observed.environment,
        )
    return ArchivePostimage(change, head, scope, active_present)


def lease_bound_archive_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...] = (),
    requested_change: str | None = None,
    official_change_complete: bool = False,
    completion_artifacts: tuple[str, ...] = (),
    preserved_archive: tuple[str, str] | None = None,
) -> dict[str, Any] | None:
    """Project a committed archive diff from official OpenSpec and Git facts."""
    del official_change_complete
    head = git_stdout(root, "rev-parse", "HEAD")
    parent = git_stdout(root, "rev-parse", f"{head}^")
    if not parent:
        return None
    paths = changed_paths or tuple(
        git_stdout(
            root,
            "diff",
            "--name-only",
            "--diff-filter=ACMRTD",
            parent,
            head,
        ).splitlines()
    )
    changes = {
        parsed[1] for path in paths if (parsed := archived_change_from_path(path)) is not None
    }
    if requested_change is not None:
        change = requested_change
        if changes and changes != {change}:
            return None
    elif len(changes) == 1:
        change = changes.pop()
    else:
        return None
    observed = _archive_scope(
        root,
        change=change,
        source_head=parent,
        tree=current_tree(root, head),
        changed_paths=paths,
        completion_artifacts=completion_artifacts,
    )
    if observed is None:
        return None
    expected_preservation = (
        (str(observed["archive_path"]), str(observed["preserved_archive_path"]))
        if observed.get("preserved_archive_path")
        else None
    )
    if preserved_archive is not None and preserved_archive != expected_preservation:
        return None
    return observed | {"state": "post_archive_closeout"}


def archive_postimage_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...],
    requested_change: str,
    tree: str,
    source_head: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    """Validate one official OpenSpec archive post-image from Git facts only."""
    head = source_head or git_stdout(root, "rev-parse", "HEAD")
    return _archive_scope(
        root,
        change=requested_change,
        source_head=head,
        tree=tree,
        changed_paths=changed_paths,
        environment=environment,
    )


def _archive_scope(
    root: Path,
    *,
    change: str,
    source_head: str,
    tree: str,
    changed_paths: tuple[str, ...],
    completion_artifacts: tuple[str, ...] = (),
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    active_root = active_change_root(change)
    source_tree = _object_id(root, f"{source_head}:{active_root}", environment=environment)
    paths = tuple(dict.fromkeys(filter(None, changed_paths)))
    archive_roots = {
        candidate for path in paths if (candidate := archive_root_from_path(path, change))
    }
    if (
        not source_tree
        or _object_id(root, f"{tree}:{active_root}", environment=environment)
        or len(archive_roots) != 1
    ):
        return None
    archive_root = archive_roots.pop()
    if _object_id(root, f"{tree}:{archive_root}", environment=environment) != source_tree:
        return None
    previous_archive_tree = _object_id(
        root,
        f"{source_head}:{archive_root}",
        environment=environment,
    )
    preservation = ""
    if previous_archive_tree:
        preservation = collision_preservation_path(archive_root, previous_archive_tree, source_head)
        if (
            _object_id(root, f"{tree}:{preservation}", environment=environment)
            != previous_archive_tree
        ):
            return None
    allowed = (f"{active_root}/", f"{archive_root}/", "openspec/specs/") + (
        (f"{preservation}/",) if preservation else ()
    )
    if not paths or any(not path.startswith(allowed) for path in paths):
        return None
    source_artifacts = _tree_paths(root, source_head, active_root, environment=environment)
    if source_artifacts is None:
        return None
    return _scope_report(
        root,
        change=change,
        archive_root=archive_root,
        changed_paths=paths,
        completion_artifacts=completion_artifacts or source_artifacts,
    ) | {
        "tree": tree,
        "archive_path": archive_root,
        "completion_artifacts": list(completion_artifacts or source_artifacts),
        **({"preserved_archive_path": preservation} if preservation else {}),
    }


def _tree_paths(
    root: Path,
    tree: str,
    path: str,
    *,
    environment: Mapping[str, str] | None = None,
) -> tuple[str, ...] | None:
    listed = run_git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        tree,
        "--",
        path,
        check=False,
        env=environment,
    )
    return None if listed.returncode else tuple(listed.stdout.splitlines())


def _object_id(
    root: Path,
    specification: str,
    *,
    environment: Mapping[str, str] | None = None,
) -> str:
    observed = run_git(root, "rev-parse", specification, check=False, env=environment)
    return observed.stdout.strip() if observed.returncode == 0 else ""


def _scope_report(
    root: Path,
    *,
    change: str,
    archive_root: str,
    changed_paths: tuple[str, ...],
    completion_artifacts: tuple[str, ...],
) -> dict[str, Any]:
    profile = load_repository_profile(root)
    if (
        profile.state == "invalid"
        or profile.declaration is None
        or profile.declaration.openspec is None
    ):
        raise ValueError(INVALID_PROFILE_ERROR)
    patterns = profile.declaration.openspec.material_paths
    material = tuple(
        path
        for path in changed_paths
        if any(repository_path_matches(path, glob) for glob in patterns)
    )
    authority_paths = {
        path: _archive_authority_path(
            path,
            change=change,
            archive_root=archive_root,
            completion_artifacts=completion_artifacts,
        )
        for path in material
    }
    covered = [
        {"path": path, "changes": [change]}
        for path, authority in authority_paths.items()
        if authority is not None
    ]
    uncovered = [path for path, authority in authority_paths.items() if authority is None]
    gaps = [f"openspec_material_path_uncovered:{path}" for path in uncovered]
    return {
        "verdict": "block" if gaps else "pass",
        "state": "archive_transition",
        "changed_paths": list(changed_paths),
        "material_patterns": list(patterns),
        "material_paths": list(material),
        "changes": [{"name": change, "path": archive_root}],
        "covered_paths": covered,
        "uncovered_paths": uncovered,
        "required_gaps": gaps,
        "advisory_gaps": [],
    }


def _archive_authority_path(
    path: str,
    *,
    change: str,
    archive_root: str,
    completion_artifacts: tuple[str, ...],
) -> str | None:
    """Map official archive output to the exact source artifact it relocated."""
    active_root = active_change_root(change)
    if path == archive_root or path.startswith(f"{archive_root}/"):
        source = active_root + path.removeprefix(archive_root)
        return source if source in completion_artifacts else None
    canonical_prefix = "openspec/specs/"
    if path.startswith(canonical_prefix):
        source = f"{active_root}/specs/{path.removeprefix(canonical_prefix)}"
        return source if source in completion_artifacts else None
    return None
