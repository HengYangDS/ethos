"""Resolve one current OpenSpec Change generation from exact start evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ethos.adapters.openspec.archive_effect import archive_generation_authority
from ethos.adapters.openspec.generation.authority import CurrentGenerationScope
from ethos.adapters.openspec.generation.authority import PathAttribution
from ethos.adapters.openspec.generation.authority import start_generation_authorities
from ethos.adapters.openspec.generation.legacy import archive_reactivation_authority
from ethos.adapters.openspec.generation.legacy import exact_initial_active_generation
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.openspec.profile import load_work_lane_commitment
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.normalization.coercion import repository_path_matches
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject


@dataclass(frozen=True, slots=True)
class CurrentGenerationBinding:
    """One selected Commitment, its Lease, and its observed generation scope."""

    lease: JsonObject
    commitment: Commitment
    scope: CurrentGenerationScope


def current_generation_binding(
    root: Path,
    *,
    status: JsonObject,
    repository_id: str,
    change: str | None = None,
    changed: bool = True,
) -> CurrentGenerationBinding:
    """Bind readers to one shared current-generation observation."""
    work_lane = status.get("role") == ROLE_WORK_LANE
    lease = leases_by_branch(root).get(str(status.get("branch") or ""), {}) if work_lane else {}
    commitment = (
        load_work_lane_commitment(root, change_id=change, lease=lease)
        if work_lane
        else load_profile_commitment(root, change_id=change)
    )
    observed = change_scope_paths_from_status(root, status) if changed else ()
    scope = (
        current_generation_scope(
            root,
            head=str(status.get("head") or ""),
            repository_id=repository_id,
            commitment=commitment,
            lease=lease,
            fallback_paths=observed,
        )
        if changed and work_lane
        else CurrentGenerationScope(observed, {})
    )
    return CurrentGenerationBinding(lease, commitment, scope)


def current_generation_scope(
    root: Path,
    *,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
    fallback_paths: tuple[str, ...],
) -> CurrentGenerationScope:
    """Resolve current paths from exact generation authority, never a train baseline."""
    change = commitment.id.removeprefix("change:")
    carrier = str(lease.get("base_commitment_path") or "")
    dirty = changed_paths(root)
    matches = start_generation_authorities(
        root,
        head=head,
        repository_id=repository_id,
        commitment=commitment,
        lease=lease,
    )
    if len(matches) == 1:
        authority = matches[0]
        previous_head = str(authority["previous_head"])
        committed = tuple(
            git_stdout(root, "diff", "--name-only", f"{previous_head}...{head}").splitlines()
        )
        paths = tuple(dict.fromkeys((*committed, *dirty)))
        return CurrentGenerationScope(
            paths,
            authority,
            attributions=_path_attributions(
                paths=tuple(dict.fromkeys((*fallback_paths, *paths))),
                selected=set(paths),
                dirty=set(dirty),
                commitment=commitment,
                change=change,
                base_head=previous_head,
                authority_id=str(authority.get("attestation_id") or ""),
            ),
            selected_carrier=carrier,
        )
    archive = archive_generation_authority(
        root,
        head=head,
        repository_id=repository_id,
        commitment=commitment,
        lease=lease,
    )
    if archive:
        authorized = tuple(string_sequence(archive.get("authorized_paths")))
        return CurrentGenerationScope(
            authorized,
            {},
            archive,
            _path_attributions(
                paths=tuple(dict.fromkeys((*fallback_paths, *authorized))),
                selected=set(authorized),
                dirty=set(),
                commitment=commitment,
                change=change,
                base_head=head,
                authority_id=str(archive.get("attestation_id") or ""),
                selected_source="archive_effect",
            ),
            carrier,
        )
    reactivation = archive_reactivation_authority(
        root,
        head=head,
        commitment=commitment,
        carrier=carrier,
    )
    if reactivation:
        base_head = str(reactivation["previous_head"])
        source_prefix = str(reactivation["source_prefix"])
        paths = tuple(
            dict.fromkeys(
                (
                    *(
                        path
                        for path in git_stdout(
                            root, "diff", "--name-only", f"{base_head}...{head}"
                        ).splitlines()
                        if not path.startswith(source_prefix)
                    ),
                    *dirty,
                )
            )
        )
        return CurrentGenerationScope(
            paths,
            reactivation,
            attributions=_path_attributions(
                paths=tuple(dict.fromkeys((*fallback_paths, *paths))),
                selected=set(paths),
                dirty=set(dirty),
                commitment=commitment,
                change=change,
                base_head=base_head,
                authority_id=str(reactivation["attestation_id"]),
                selected_source="archive_reactivation",
            ),
            selected_carrier=carrier,
        )
    if exact_initial_active_generation(
        root,
        head=head,
        commitment=commitment,
        carrier=carrier,
        fallback_paths=fallback_paths,
    ):
        return CurrentGenerationScope(
            fallback_paths,
            {},
            attributions=_path_attributions(
                paths=fallback_paths,
                selected=set(fallback_paths),
                dirty=set(dirty),
                commitment=commitment,
                change=change,
                base_head="",
                authority_id="",
                selected_source="initial_active_generation",
            ),
            selected_carrier=carrier,
        )
    return CurrentGenerationScope(
        (),
        {},
        attributions=tuple(
            PathAttribution(
                path=path,
                source="unresolved_lane_delta",
                state="unknown",
                change_id=change,
                generation_base_head="",
            )
            for path in fallback_paths
        ),
        selected_carrier=carrier,
        gaps=(
            ("change_generation_authority_missing",)
            if fallback_paths
            and str(lease.get("expected_head") or "") == head
            and not str(lease.get("base_commitment_path") or "").startswith(
                "openspec/changes/archive/"
            )
            else ()
        ),
    )


def _path_attributions(
    *,
    paths: tuple[str, ...],
    selected: set[str],
    dirty: set[str],
    commitment: Commitment,
    change: str,
    base_head: str,
    authority_id: str,
    selected_source: str = "generation_commit",
) -> tuple[PathAttribution, ...]:
    projections: list[PathAttribution] = []
    for path in paths:
        pattern = next(
            (
                candidate
                for candidate in commitment.scope
                if repository_path_matches(path, candidate)
            ),
            "",
        )
        current = path in selected
        projections.append(
            PathAttribution(
                path=path,
                source=("dirty_overlay" if path in dirty else selected_source)
                if current
                else "historical_lane_delta",
                state=("authorized" if pattern else "uncovered") if current else "historical",
                change_id=change,
                generation_base_head=base_head,
                authority_id=authority_id if current else "",
                matched_pattern=pattern if current else "",
            )
        )
    return tuple(projections)
