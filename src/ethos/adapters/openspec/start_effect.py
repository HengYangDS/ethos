"""Compile the current OpenSpec acceptance binding from fresh repository facts."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from ethos.adapters.openspec.lifecycle.archive_transition import attested_archive_transition
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.contracts.branch.roles import ROLE_WORK_LANE

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.admission.lease_binding import CurrentAuthority
    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject


@dataclass(frozen=True, slots=True)
class PathAttribution:
    """Explain one changed path as a fresh Git observation, not an authorization."""

    path: str
    source: str
    state: str
    change_id: str

    def projection(self) -> JsonObject:
        """Return the stable machine projection used by reader surfaces."""
        return {
            "path": self.path,
            "source": self.source,
            "state": self.state,
            "change_id": self.change_id,
        }


@dataclass(frozen=True, slots=True)
class CurrentGenerationScope:
    """Fresh changed paths associated with one selected official Change."""

    paths: tuple[str, ...]
    start_authority: JsonObject = field(default_factory=dict)
    archive_authority: JsonObject = field(default_factory=dict)
    attributions: tuple[PathAttribution, ...] = ()
    selected_carrier: str = ""
    gaps: tuple[str, ...] = ()

    def attribution_projection(self) -> tuple[JsonObject, ...]:
        """Return deterministic path observations for public readers."""
        return tuple(item.projection() for item in self.attributions)


@dataclass(frozen=True, slots=True)
class CurrentGenerationBinding:
    """Bind one compiled Commitment to fresh changed paths."""

    lease: JsonObject
    commitment: Commitment
    scope: CurrentGenerationScope

    @property
    def change_id(self) -> str:
        """Return the selected official Change identity."""
        return self.commitment.id.removeprefix("change:")

    def scope_report(self, paths: tuple[str, ...] | None = None) -> JsonObject:
        """Project the selected generation as one material-path authority."""
        authorized = tuple(dict.fromkeys(self.scope.paths))
        observed = tuple(dict.fromkeys(paths if paths is not None else authorized))
        change = self.change_id
        covered = tuple(path for path in observed if path in authorized)
        uncovered = tuple(path for path in observed if path not in authorized)
        gaps = (
            *self.scope.gaps,
            *(f"openspec_material_path_uncovered:{path}" for path in uncovered),
        )
        return {
            "verdict": "block" if gaps else "pass",
            "state": ("archive_attested" if self.scope.archive_authority else "attributed"),
            "changed_paths": list(observed),
            "material_patterns": [],
            "material_paths": list(observed),
            "changes": [{"name": change}],
            "covered_paths": [{"path": path, "changes": [change]} for path in covered],
            "uncovered_paths": list(uncovered),
            "required_gaps": list(gaps),
            "advisory_gaps": [],
        }


def current_generation_binding(
    root: Path,
    *,
    status: JsonObject,
    repository_id: str,
    authority: CurrentAuthority | None = None,
    change: str | None = None,
    changed: bool = True,
) -> CurrentGenerationBinding:
    """Compile acceptance from OpenSpec and paths from the current Git checkout."""
    del repository_id
    work_lane = status.get("role") == ROLE_WORK_LANE
    if work_lane and (authority is None or authority.verdict != "pass"):
        reason = authority.reason if authority is not None else "current_authority_unavailable"
        raise ValueError(reason)
    archive_authority: JsonObject = {}
    try:
        commitment = load_profile_commitment(root, change_id=change)
    except ValueError as error:
        if str(error) != "openspec_active_change_missing":
            raise
        archived = attested_archive_transition(
            root,
            head=str(status.get("head") or ""),
            change=change,
        )
        if archived is None:
            raise
        commitment, archive_authority = archived
    observed_paths = change_scope_paths_from_status(root, status) if changed else ()
    authorized_paths = archive_authority.get("authorized_paths")
    paths = (
        tuple(str(path) for path in authorized_paths)
        if archive_authority and isinstance(authorized_paths, list | tuple)
        else observed_paths
    )
    scope = current_generation_scope(
        root,
        head=str(status.get("head") or ""),
        repository_id="",
        commitment=commitment,
        lease=authority.lease if authority is not None else {},
        fallback_paths=paths,
        current_binding=work_lane,
    )
    if archive_authority:
        scope = CurrentGenerationScope(
            paths=scope.paths,
            archive_authority=archive_authority,
            attributions=scope.attributions,
        )
    return CurrentGenerationBinding(
        authority.lease if authority is not None else {}, commitment, scope
    )


def current_generation_scope(
    root: Path,
    *,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
    fallback_paths: tuple[str, ...],
    current_binding: bool = False,
) -> CurrentGenerationScope:
    """Return only fresh path facts; no carrier, lineage, or Lease scope is consulted."""
    del root, head, repository_id, lease, current_binding
    paths = tuple(dict.fromkeys(fallback_paths))
    change = commitment.id.removeprefix("change:")
    return CurrentGenerationScope(
        paths=paths,
        attributions=tuple(
            PathAttribution(path, "git_changed_path", "observed", change) for path in paths
        ),
    )
