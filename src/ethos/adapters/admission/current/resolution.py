"""Resolve current authority, official acceptance intent, and fresh path facts once."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.lifecycle.archive_transition import attested_archive_transition
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.semantic import Commitment
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.admission.current.authority import CurrentAuthority
    from ethos.contracts.value import JsonObject
    from ethos.contracts.verdict import Verdict


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
class CurrentScope:
    """Fresh changed paths associated with one selected official Change."""

    paths: tuple[str, ...]
    start_authority: JsonObject = field(default_factory=dict)
    archive_authority: JsonObject = field(default_factory=dict)
    attributions: tuple[PathAttribution, ...] = ()
    selected_carrier: str = ""
    gaps: tuple[str, ...] = ()
    material_scope: JsonObject = field(default_factory=dict)

    def attribution_projection(self) -> tuple[JsonObject, ...]:
        """Return deterministic path observations for public readers."""
        return tuple(item.projection() for item in self.attributions)


@dataclass(frozen=True, slots=True)
class CurrentResolution:
    """Own one current authority and official acceptance resolution."""

    verdict: Verdict
    authority: CurrentAuthority | None
    commitment: Commitment | None
    scope: CurrentScope
    openspec: JsonObject = field(default_factory=dict)
    required_gaps: tuple[str, ...] = ()
    next_action: str = ""
    user_decision_required: bool = False

    @property
    def lease(self) -> JsonObject:
        """Return the minimal current Lease projection for plan inputs."""
        return self.authority.lease if self.authority is not None else {}

    @property
    def change_id(self) -> str:
        """Return the selected official Change identity when available."""
        return self.commitment.id.removeprefix("change:") if self.commitment is not None else ""

    def scope_report(self, paths: tuple[str, ...] | None = None) -> JsonObject:
        """Project the selected Change as one material-path observation."""
        if self.scope.material_scope and not self.scope.archive_authority:
            return dict(self.scope.material_scope)
        if self.verdict != "pass":
            return {
                "verdict": self.verdict,
                "state": "not_available",
                "changed_paths": list(paths or self.scope.paths),
                "material_patterns": [],
                "material_paths": [],
                "changes": [],
                "covered_paths": [],
                "uncovered_paths": [],
                "required_gaps": list(self.required_gaps),
                "advisory_gaps": [],
            }
        authorized = tuple(
            dict.fromkeys(
                cast(
                    "tuple[str, ...]",
                    tuple(self.scope.archive_authority.get("authorized_paths", ())),
                )
                if self.scope.archive_authority
                else self.scope.paths
            )
        )
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
            "state": "archive_attested" if self.scope.archive_authority else "attributed",
            "changed_paths": list(observed),
            "material_patterns": [],
            "material_paths": list(observed),
            "changes": [{"name": change}] if change else [],
            "covered_paths": [{"path": path, "changes": [change]} for path in covered],
            "uncovered_paths": list(uncovered),
            "required_gaps": list(gaps),
            "advisory_gaps": [],
        }


def _intent_action(root: Path, gap: str, change: str | None) -> str:
    if gap == "openspec_official_cli_missing":
        return "npm ci --ignore-scripts --no-audit --no-fund"
    if change:
        return f"openspec status --change {change} --json"
    return f"ethos status --root {root.resolve().as_posix()} --json"


def resolve_current_resolution(
    root: Path,
    *,
    status: JsonObject,
    authority: CurrentAuthority | None = None,
    change: str | None = None,
    changed: bool = True,
) -> CurrentResolution:
    """Resolve current authority, official intent, paths, gap, and action once."""
    work_lane = status.get("role") == ROLE_WORK_LANE
    if work_lane and (authority is None or authority.verdict != "pass"):
        gap = authority.reason if authority is not None else "current_authority_unavailable"
        action, user_decision = (
            authority.recovery(root)
            if authority is not None
            else (f"ethos lane status --root {root.resolve().as_posix()} --json", False)
        )
        return CurrentResolution(
            verdict=authority.verdict if authority is not None else "unknown",
            authority=authority,
            commitment=None,
            scope=CurrentScope(()),
            required_gaps=(gap,),
            next_action=action,
            user_decision_required=user_decision,
        )
    observed_paths = change_scope_paths_from_status(root, status) if changed else ()
    official = openspec_governance_report(
        root,
        change=change,
        lifecycle=True,
        changed_paths=observed_paths,
        require_workspace=False,
    )
    official_verdict = report_verdict(official)
    official_gaps = tuple(string_sequence(official.get("required_gaps")))
    lifecycle = official.get("lifecycle")
    material_scope = (
        string_mapping(lifecycle.get("scope_binding"))
        if isinstance(lifecycle, dict) and isinstance(lifecycle.get("scope_binding"), dict)
        else {}
    )
    if official_verdict != "pass":
        gap = official_gaps[0] if official_gaps else "openspec_scope_unavailable"
        return CurrentResolution(
            verdict=official_verdict,
            authority=authority,
            commitment=None,
            scope=CurrentScope(
                observed_paths,
                gaps=official_gaps or (gap,),
                material_scope=material_scope,
            ),
            openspec=official,
            required_gaps=official_gaps or (gap,),
            next_action=_intent_action(root, gap, change),
        )
    archive_authority: JsonObject = {}
    try:
        projected = official.get("commitment")
        commitment = (
            Commitment.model_validate(projected)
            if isinstance(projected, dict)
            else load_profile_commitment(root, change_id=change)
        )
    except ValueError as error:
        gap = str(error)
        missing = "openspec_active_change_missing"
        selected_missing = f"openspec_show_failed:{change}" if change is not None else ""
        if gap in {missing, selected_missing}:
            archived = attested_archive_transition(
                root,
                head=str(status.get("head") or ""),
                change=change,
            )
            if archived is not None:
                commitment, archive_authority = archived
            else:
                return CurrentResolution(
                    verdict="block",
                    authority=authority,
                    commitment=None,
                    scope=CurrentScope(()),
                    openspec=official,
                    required_gaps=(gap,),
                    next_action=_intent_action(root, gap, change),
                )
        else:
            return CurrentResolution(
                verdict="block",
                authority=authority,
                commitment=None,
                scope=CurrentScope(()),
                openspec=official,
                required_gaps=(gap,),
                next_action=_intent_action(root, gap, change),
            )
    scope = current_scope(
        commitment=commitment,
        fallback_paths=observed_paths,
        material_scope=material_scope,
    )
    if archive_authority:
        scope = CurrentScope(
            paths=scope.paths,
            archive_authority=archive_authority,
            attributions=scope.attributions,
            material_scope=scope.material_scope,
        )
    return CurrentResolution(
        verdict="pass",
        authority=authority,
        commitment=commitment,
        scope=scope,
        openspec=official,
    )


def current_scope(
    *,
    commitment: Commitment,
    fallback_paths: tuple[str, ...],
    material_scope: JsonObject | None = None,
) -> CurrentScope:
    """Return fresh path facts without carrier, lineage, or Lease scope."""
    paths = tuple(dict.fromkeys(fallback_paths))
    change = commitment.id.removeprefix("change:")
    return CurrentScope(
        paths=paths,
        attributions=tuple(
            PathAttribution(path, "git_changed_path", "observed", change) for path in paths
        ),
        material_scope=material_scope or {},
    )
