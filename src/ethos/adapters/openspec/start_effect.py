"""Resolve one current OpenSpec Change generation from exact start evidence."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.mutation.proof_artifacts import attestation_store_dir
from ethos.adapters.mutation.proof_artifacts import scan_attestations
from ethos.adapters.openspec.archive_effect import archive_generation_authority
from ethos.adapters.openspec.generation.legacy import archive_reactivation_authority
from ethos.adapters.openspec.generation.legacy import exact_initial_active_generation
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.openspec.profile import load_work_lane_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import integer
from ethos.normalization.coercion import repository_path_matches
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation
    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject


@dataclass(frozen=True, slots=True)
class PathAttribution:
    """Explain why one observed path does or does not belong to this generation."""

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
    """One current Change generation scope and its exact start receipt."""

    paths: tuple[str, ...]
    start_authority: JsonObject
    archive_authority: JsonObject = field(default_factory=dict)
    attributions: tuple[PathAttribution, ...] = ()
    selected_carrier: str = ""
    gaps: tuple[str, ...] = ()

    def attribution_projection(self) -> tuple[JsonObject, ...]:
        """Return deterministic path provenance for public planning surfaces."""
        return tuple(item.projection() for item in self.attributions)


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
    matches = tuple(
        authority
        for attestation in scan_attestations(attestation_store_dir(root))[0]
        if (
            authority := _start_authority(
                root,
                attestation=attestation,
                head=head,
                repository_id=repository_id,
                commitment=commitment,
                lease=lease,
            )
        )
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
            if fallback_paths and str(lease.get("expected_head") or "") == head
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


def _start_authority(
    root: Path,
    *,
    attestation: Attestation,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
) -> JsonObject:
    statement = attestation.statement
    values = tuple(
        _mapping(statement.get(name))
        for name in ("input", "output", "claim", "result", "freshness")
    )
    if any(value is None for value in values):
        return {}
    input_data, output, claim, result, freshness = cast(
        "tuple[JsonObject, JsonObject, JsonObject, JsonObject, JsonObject]", values
    )
    previous_head = str(input_data.get("head") or "")
    start_head = str(output.get("head") or "")
    change = commitment.id.removeprefix("change:")
    before, after = _generation(input_data.get("lease")), _generation(output.get("lease"))
    current = lease_generation(lease)
    try:
        started_commitment = (
            load_lease_bound_commitment(root, lease=after, change_id=change)
            if after is not None
            else None
        )
    except ValueError:
        started_commitment = None
    valid = (
        attestation.predicate == "effect:openspec-change-start"
        and attestation.verdict == "pass"
        and started_commitment is not None
        and attestation.commitment_digest == started_commitment.digest()
        and statement.get("repository") == repository_id
        and claim == {"operation": "openspec.change.start", "effect": attestation.effect_digest}
        and result == {"state": "applied", "executed": True, "exit_code": 0}
        and output.get("head") == start_head
        and before is not None
        and after is not None
        and after.get("branch") == current.get("branch")
        and after.get("lane_incarnation_id") == current.get("lane_incarnation_id")
        and after.get("lease_id") == current.get("lease_id")
        and integer(after.get("epoch"), default=-1) <= integer(current.get("epoch"), default=-1)
        and after.get("expected_head") == start_head
        and after.get("expected_tree") == current_tree(root, start_head)
        and current.get("expected_head") == head
        and current.get("expected_tree") == current_tree(root, head)
        and current.get("base_commitment_path") == f"openspec/changes/{change}/commitment.toml"
        and before.get("expected_head") == previous_head
        and before.get("expected_tree") == current_tree(root, previous_head)
        and before.get("branch") == after.get("branch")
        and before.get("lane_incarnation_id") == after.get("lane_incarnation_id")
        and before.get("lease_id") == after.get("lease_id")
        and before.get("holder_ref") == after.get("holder_ref")
        and before.get("epoch") == after.get("epoch", 0) - 1
        and str(before.get("base_commitment_path") or "").startswith("openspec/changes/archive/")
        and after.get("base_commitment_path") == f"openspec/changes/{change}/commitment.toml"
        and git_stdout(root, "rev-parse", f"{start_head}^") == previous_head
        and is_ancestor(root, start_head, head)
        and freshness.get("repository") == repository_id
        and freshness.get("subject")
        == {"change": change, "previous_head": previous_head, "head": start_head}
        and freshness.get("change") == change
        and freshness.get("previous_head") == previous_head
        and freshness.get("head") == start_head
        and freshness.get("output_digest") == canonical_json_digest(output)
        and statement.get("input_digest") == canonical_json_digest(input_data)
        and statement.get("output_digest")
        == canonical_json_digest({"result": result, "output": output})
        and attestation.effect_digest
        == canonical_json_digest(
            {
                "predicate": attestation.predicate,
                "operation": claim.get("operation"),
                "command": statement.get("command"),
                "subject": freshness.get("subject"),
                "before": input_data,
                "after": output,
            }
        )
    )
    if not valid:
        return {}
    return {
        "predicate": attestation.predicate,
        "attestation_id": attestation.id,
        "commitment_digest": attestation.commitment_digest,
        "effect_digest": attestation.effect_digest,
        "repository": statement.get("repository"),
        "claim": claim,
        "result": result,
        "input": input_data,
        "output": output,
        "freshness": freshness,
        "previous_head": previous_head,
    }


def _mapping(value: object) -> JsonObject | None:
    normalized = mutable_json(value)
    return (
        {str(key): item for key, item in normalized.items()}
        if isinstance(normalized, dict)
        else None
    )


def _generation(value: object) -> JsonObject | None:
    normalized = _mapping(value)
    if normalized is None:
        return None
    expected = lease_generation(
        {
            "lane_ref": normalized.get("branch"),
            "lane_incarnation_id": normalized.get("lane_incarnation_id"),
            "lease_id": normalized.get("lease_id"),
            "epoch": normalized.get("epoch"),
            "holder_ref": normalized.get("holder_ref"),
            "expected_head": normalized.get("expected_head"),
            "expected_tree": normalized.get("expected_tree"),
            "base_commitment_path": normalized.get("base_commitment_path"),
            "base_commitment_bytes_sha256": normalized.get("base_commitment_bytes_sha256"),
            "base_commitment_digest": normalized.get("base_commitment_digest"),
            "issued_at": normalized.get("issued_at"),
            "renewed_at": normalized.get("renewed_at"),
            "path_scope": normalized.get("path_scope"),
            "expires_at": normalized.get("expires_at"),
            "payload_sha256": normalized.get("payload_sha256"),
        }
    )
    return normalized if mutable_json(expected) == normalized else None
