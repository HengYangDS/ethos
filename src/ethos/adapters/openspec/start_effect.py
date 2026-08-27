"""Observe one current OpenSpec generation from exact Git and effect facts."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_evidence import (
    rebind_generation_authority,
)
from ethos.adapters.openspec.generation.attestation import start_effect_authority
from ethos.adapters.openspec.lifecycle.archive_effect import archive_effect_authority
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.commitment import commitment_generation_origin
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import committed_file_bytes
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.semantic import canonical_json_digest
from ethos.normalization.coercion import repository_path_matches
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.admission.lease_binding import CurrentAuthority
    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject


@dataclass(frozen=True, slots=True)
class PathAttribution:
    """Explain why one observed path belongs to the selected generation."""

    path: str
    source: str
    state: str
    change_id: str
    generation_base_head: str
    authority_id: str = ""
    matched_pattern: str = ""

    def projection(self) -> JsonObject:
        """Return the stable machine projection carried by plans and receipts."""
        return {
            "path": self.path,
            "source": self.source,
            "state": self.state,
            "change_id": self.change_id,
            "generation_base_head": self.generation_base_head,
            "authority_id": self.authority_id,
            "matched_pattern": self.matched_pattern,
        }


@dataclass(frozen=True, slots=True)
class CurrentGenerationScope:
    """One immutable OpenSpec generation observation and its exact authority."""

    paths: tuple[str, ...]
    start_authority: JsonObject
    archive_authority: JsonObject = field(default_factory=dict)
    attributions: tuple[PathAttribution, ...] = ()
    selected_carrier: str = ""
    gaps: tuple[str, ...] = ()

    def attribution_projection(self) -> tuple[JsonObject, ...]:
        """Return deterministic path provenance for public reader surfaces."""
        return tuple(item.projection() for item in self.attributions)


@dataclass(frozen=True, slots=True)
class CurrentGenerationBinding:
    """Bind one Commitment and Lease to one generation observation."""

    lease: JsonObject
    commitment: Commitment
    scope: CurrentGenerationScope

    @property
    def change_id(self) -> str | None:
        """Return the selected logical Change identity, if this is one."""
        return (
            self.commitment.id.removeprefix("change:")
            if self.commitment.id.startswith("change:")
            else None
        )


def current_generation_binding(
    root: Path,
    *,
    status: JsonObject,
    repository_id: str,
    authority: CurrentAuthority | None = None,
    change: str | None = None,
    changed: bool = True,
) -> CurrentGenerationBinding:
    """Bind all readers to one shared current-generation observation."""
    work_lane = status.get("role") == ROLE_WORK_LANE
    if work_lane:
        if authority is None or authority.commitment is None:
            msg = f"current_authority_unavailable:{status.get('branch') or ''}"
            raise ValueError(msg)
        lease = authority.lease
        commitment = authority.commitment
    else:
        lease = {}
        commitment = load_profile_commitment(root, change_id=change)
    observed = change_scope_paths_from_status(root, status) if changed else ()
    scope = (
        current_generation_scope(
            root,
            head=str(status.get("head") or ""),
            repository_id=repository_id,
            commitment=commitment,
            lease=lease,
            fallback_paths=observed,
            current_binding=authority is not None and authority.verdict == "pass",
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
    current_binding: bool = False,
) -> CurrentGenerationScope:
    """Observe exact start/archive authority once and select current paths."""
    change = commitment.id.removeprefix("change:")
    carrier = str(lease.get("base_commitment_path") or "")
    dirty = changed_paths(root)
    start, archive = _effect_authorities(
        root,
        head=head,
        repository_id=repository_id,
        commitment=commitment,
        lease=lease,
    )
    rebound = tuple(item for item in start if item.get("source") == "rebind_generation")
    start = rebound or start
    if len(start) == 1:
        authority = start[0]
        base = str(authority["previous_head"])
        paths = tuple(
            dict.fromkeys(
                (*git_stdout(root, "diff", "--name-only", f"{base}...{head}").splitlines(), *dirty)
            )
        )
        return _scope(
            paths,
            authority,
            {},
            fallback_paths,
            dirty,
            commitment,
            change,
            base,
            carrier,
            source=str(authority.get("source") or "generation_commit"),
        )
    if len(archive) == 1:
        authority = archive[0]
        paths = tuple(string_sequence(authority.get("authorized_paths")))
        return _scope(
            paths,
            {},
            authority,
            fallback_paths,
            (),
            commitment,
            change,
            head,
            carrier,
            source="archive_effect",
        )
    reactivation = _archive_reactivation(root, head, commitment, carrier)
    if reactivation:
        base = str(reactivation["previous_head"])
        prefix = str(reactivation["source_prefix"])
        paths = tuple(
            dict.fromkeys(
                (
                    *(
                        path
                        for path in git_stdout(
                            root, "diff", "--name-only", f"{base}...{head}"
                        ).splitlines()
                        if not path.startswith(prefix)
                    ),
                    *dirty,
                )
            )
        )
        return _scope(
            paths,
            reactivation,
            {},
            fallback_paths,
            dirty,
            commitment,
            change,
            base,
            carrier,
            source="archive_reactivation",
        )
    if base := _initial_generation(root, head, commitment, carrier, fallback_paths):
        return _scope(
            fallback_paths,
            {},
            {},
            fallback_paths,
            dirty,
            commitment,
            change,
            base,
            carrier,
            source="initial_active_generation",
        )
    return CurrentGenerationScope(
        fallback_paths if current_binding else (),
        {},
        attributions=tuple(
            PathAttribution(
                path,
                "current_lease_binding" if current_binding else "unresolved_lane_delta",
                "unknown"
                if not current_binding
                else "authorized"
                if any(repository_path_matches(path, pattern) for pattern in commitment.scope)
                else "uncovered",
                change,
                str(lease.get("expected_head") or "") if current_binding else "",
                str(lease.get("lease_id") or "") if current_binding else "",
                next(
                    (
                        pattern
                        for pattern in commitment.scope
                        if repository_path_matches(path, pattern)
                    ),
                    "",
                )
                if current_binding
                else "",
            )
            for path in fallback_paths
        ),
        selected_carrier=carrier,
    )


def _effect_authorities(
    root: Path,
    *,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
) -> tuple[tuple[JsonObject, ...], tuple[JsonObject, ...]]:
    start: list[JsonObject] = []
    archive: list[JsonObject] = []
    _selected_root, attestations = read_attestation_set(root)
    for attestation in attestations:
        if attestation.predicate == "effect:openspec-change-start":
            projection = start_effect_authority(
                root, attestation, head, repository_id, commitment, lease
            )
            if projection:
                start.append(projection)
        elif attestation.predicate == "effect:openspec-archive":
            projection = archive_effect_authority(
                root, attestation, head, repository_id, commitment, lease
            )
            if projection:
                archive.append(projection)
        elif attestation.predicate == "effect:commitment-rebind":
            projection = rebind_generation_authority(
                root,
                attestation,
                repository_id=repository_id,
                commitment_digest=commitment.digest(),
                lease=lease,
                attestations=attestations,
            )
            if projection:
                start.append(projection)
    return tuple(start), tuple(archive)


def _initial_generation(
    root: Path,
    head: str,
    commitment: Commitment,
    carrier: str,
    fallback_paths: tuple[str, ...],
) -> str:
    if not carrier or not fallback_paths:
        return ""
    base = commitment_generation_origin(
        root,
        head=head,
        carrier=carrier,
        change_id=commitment.id.removeprefix("change:"),
    )
    return (
        base
        if (
            base
            and carrier.startswith("openspec/changes/")
            and not carrier.startswith("openspec/changes/archive/")
            and not committed_file_bytes(root, base, carrier)
            and bool(committed_file_bytes(root, head, carrier))
            and not _archived_carriers(root, base, commitment.id.removeprefix("change:"))
            and all(
                any(repository_path_matches(path, pattern) for pattern in commitment.scope)
                for path in fallback_paths
            )
        )
        else ""
    )


def _archive_reactivation(
    root: Path, head: str, commitment: Commitment, carrier: str
) -> JsonObject:
    policy = load_branch_role_policy(root)
    histories = tuple(
        (base, commits)
        for branch in (policy.candidate_branch, policy.accepted_branch)
        if (base := git_stdout(root, "rev-parse", "--verify", branch))
        and is_ancestor(root, base, head)
        and (commits := git_stdout(root, "rev-list", "--reverse", f"{base}..{head}").splitlines())
    )
    if not histories:
        return {}
    base, commits = min(histories, key=lambda item: len(item[1]))
    restored = commits[0]
    change = commitment.id.removeprefix("change:")
    sources = _archived_carriers(root, base, change)
    if git_stdout(root, "rev-parse", f"{restored}^") != base or len(sources) != 1:
        return {}
    source = sources[0]
    source_prefix, target_prefix = (
        source.removesuffix("commitment.toml"),
        carrier.removesuffix("commitment.toml"),
    )
    source_paths = tuple(
        path
        for path in git_stdout(root, "ls-tree", "-r", "--name-only", base).splitlines()
        if path.startswith(source_prefix)
    )
    stable = any(
        committed_file_bytes(root, base, path)
        == committed_file_bytes(
            root, restored, f"{target_prefix}{path.removeprefix(source_prefix)}"
        )
        != b""
        for path in source_paths
        if path.endswith("/.openspec.yaml") or "/specs/" in path
    )
    valid = (
        carrier
        and not committed_file_bytes(root, base, carrier)
        and not committed_file_bytes(root, restored, source)
        and bool(committed_file_bytes(root, restored, carrier))
        and not any(committed_file_bytes(root, restored, path) for path in source_paths)
        and stable
    )
    return (
        {
            "predicate": "effect:openspec-archive-reactivation",
            "attestation_id": canonical_json_digest(
                {
                    "generation_base": base,
                    "restored_head": restored,
                    "source": source,
                    "target": carrier,
                }
            ),
            "previous_head": base,
            "restored_head": restored,
            "source_carrier": source,
            "source_prefix": source_prefix,
            "target_carrier": carrier,
        }
        if valid
        else {}
    )


def _archived_carriers(root: Path, head: str, change: str) -> tuple[str, ...]:
    matches: list[str] = []
    for path in git_stdout(root, "ls-tree", "-r", "--name-only", head).splitlines():
        if not (path.startswith("openspec/changes/archive/") and path.endswith("/commitment.toml")):
            continue
        try:
            load_commitment(root, carrier=path, change_id=change, tree_ref=head)
        except ValueError:
            continue
        matches.append(path)
    return tuple(matches)


def _scope(
    paths: tuple[str, ...],
    start: JsonObject,
    archive: JsonObject,
    fallback: tuple[str, ...],
    dirty: tuple[str, ...] | set[str],
    commitment: Commitment,
    change: str,
    base: str,
    carrier: str,
    *,
    source: str = "generation_commit",
) -> CurrentGenerationScope:
    selected, dirty_paths = set(paths), set(dirty)
    archive_paths = set(string_sequence(archive.get("authorized_paths")))
    attributions: list[PathAttribution] = []
    for path in dict.fromkeys((*fallback, *paths)):
        current = path in selected
        effect_authorized = current and source == "archive_effect" and path in archive_paths
        pattern = (
            "effect:openspec-archive"
            if effect_authorized
            else next(
                (item for item in commitment.scope if repository_path_matches(path, item)), ""
            )
        )
        attributions.append(
            PathAttribution(
                path,
                ("dirty_overlay" if path in dirty_paths else source)
                if current
                else "historical_lane_delta",
                ("authorized" if pattern else "uncovered") if current else "historical",
                change,
                base,
                str((start or archive).get("attestation_id") or "") if current else "",
                pattern if current else "",
            )
        )
    return CurrentGenerationScope(paths, start, archive, tuple(attributions), carrier)
