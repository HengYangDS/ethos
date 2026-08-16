"""Validate exact OpenSpec start and archive effect attestations."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestation_once
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git_effect_attestation import NativeEffect
from ethos.adapters.repo.git_effect_attestation import issue_native_effect
from ethos.adapters.repo.git_effect_attestation import native_effect_result
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import integer
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.value import JsonObject

_START_ATTESTATION_COLLISION = "openspec_change_start_attestation_collision"
_START_ATTESTATION_MISSING = "openspec_change_start_attestation_missing"


def start_effect_authority(
    root: Path,
    attestation: Attestation,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
) -> JsonObject:
    if not recognized_operation_attestation(attestation, "effect:openspec-change-start"):
        return {}
    statement = attestation.payload.body
    values = tuple(
        semantic_mapping(statement.get(name))
        for name in ("input", "output", "claim", "result", "freshness")
    )
    if any(value is None for value in values):
        return {}
    before, output, claim, result, freshness = cast(
        "tuple[JsonObject, JsonObject, JsonObject, JsonObject, JsonObject]", values
    )
    previous_head = str(before.get("head") or "")
    start_head = str(output.get("head") or "")
    change = commitment.id.removeprefix("change:")
    old, new, current = (
        _generation(before.get("lease")),
        _generation(output.get("lease")),
        lease_generation(lease),
    )
    try:
        started = load_lease_bound_commitment(root, lease=new, change_id=change) if new else None
    except ValueError:
        started = None
    valid = (
        started is not None
        and started.id == commitment.id
        and attestation.commitment_digest == started.digest()
        and statement.get("repository") == repository_id
        and claim == {"operation": "openspec.change.start", "effect": attestation.effect_digest}
        and result in (native_effect_result("applied"), native_effect_result("prepared"))
        and old is not None
        and new is not None
        and new.get("branch") == current.get("branch")
        and new.get("lane_incarnation_id") == current.get("lane_incarnation_id")
        and new.get("lease_id") == current.get("lease_id")
        and new.get("holder_ref") == current.get("holder_ref")
        and integer(new.get("epoch"), default=-1) <= integer(current.get("epoch"), default=-1)
        and new.get("expected_head") == start_head
        and new.get("expected_tree") == current_tree(root, start_head)
        and current.get("expected_head") == head
        and current.get("expected_tree") == current_tree(root, head)
        and current.get("base_commitment_path") == f"openspec/changes/{change}/commitment.toml"
        and old.get("expected_head") == previous_head
        and old.get("expected_tree") == current_tree(root, previous_head)
        and commitment.predecessors == (str(old.get("base_commitment_digest")),)
        and all(
            old.get(name) == new.get(name)
            for name in ("branch", "lane_incarnation_id", "lease_id", "holder_ref")
        )
        and old.get("epoch") == new.get("epoch", 0) - 1
        and str(old.get("base_commitment_path") or "").startswith("openspec/changes/archive/")
        and new.get("base_commitment_path") == f"openspec/changes/{change}/commitment.toml"
        and git_stdout(root, "rev-parse", f"{start_head}^") == previous_head
        and is_ancestor(root, start_head, head)
        and freshness.get("subject")
        == {"change": change, "previous_head": previous_head, "head": start_head}
        and freshness.get("output_digest") == canonical_json_digest(output)
        and statement.get("input_digest") == canonical_json_digest(before)
        and statement.get("output_digest")
        == canonical_json_digest({"result": result, "output": output})
        and attestation.effect_digest
        == operation_effect_digest(attestation, claim, freshness, before, output)
    )
    return (
        operation_projection(attestation, statement, claim, result, freshness, before, output)
        | {"previous_head": previous_head}
        if valid
        else {}
    )


def archive_effect_authority(
    root: Path,
    attestation: Attestation,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
) -> JsonObject:
    """Return exact archive authority projected from one valid Attestation."""
    if not recognized_operation_attestation(attestation, "effect:openspec-archive"):
        return {}
    statement = attestation.payload.body
    values = tuple(
        semantic_mapping(statement.get(name)) for name in ("output", "claim", "result", "freshness")
    )
    if any(value is None for value in values):
        return {}
    output, claim, result, freshness = cast(
        "tuple[JsonObject, JsonObject, JsonObject, JsonObject]", values
    )
    archive_path = str(output.get("archive_path") or "")
    paths = tuple(string_sequence(output.get("changed_paths")))
    before = statement.get("input")
    valid = (
        attestation.commitment_digest == commitment.digest()
        and statement.get("repository") == repository_id
        and claim == {"operation": "openspec.archive", "effect": attestation.effect_digest}
        and result == native_effect_result("applied")
        and output.get("head") == head
        and output.get("tree") == current_tree(root, head)
        and lease_binding(output.get("lease")) == lease_binding(lease)
        and freshness.get("output_digest") == canonical_json_digest(output)
        and statement.get("input_digest") == canonical_json_digest(before)
        and statement.get("output_digest")
        == canonical_json_digest({"result": result, "output": output})
        and attestation.effect_digest
        == operation_effect_digest(attestation, claim, freshness, before, output)
        and exact_archive_paths(root, head, archive_path, paths)
    )
    return (
        operation_projection(attestation, statement, claim, result, freshness, before, output)
        | {"authorized_paths": list(paths)}
        if valid
        else {}
    )


def issue_archive_effect(
    root: Path,
    *,
    change: str,
    previous_head: str,
    head: str,
    archive_path: str,
    changed_paths: tuple[str, ...],
    lease: dict[str, object],
) -> Attestation:
    """Issue one exact committed archive effect Attestation."""
    repository = load_repository_commitment(root, tree_ref=head)
    commitment = load_commitment(
        root, carrier=f"{archive_path}/commitment.toml", change_id=change, tree_ref=head
    )
    return issue_native_effect(
        root,
        effect=NativeEffect(
            predicate="effect:openspec-archive",
            operation="openspec.archive",
            command=openspec_cli.archive_command(
                root, change, tree_ref=head, archive_path=archive_path
            ),
            subject={
                "change": change,
                "archive_path": archive_path,
                "tool_version": openspec_cli.OFFICIAL_VERSION,
            },
            before={
                "head": previous_head,
                "tree": current_tree(root, previous_head),
                "commitment_digest": commitment.digest(),
            },
            after={
                "head": head,
                "tree": current_tree(root, head),
                "archive_path": archive_path,
                "changed_paths": changed_paths,
                "lease": lease_binding(lease),
            },
        ),
        state="applied",
        commitment_digest=commitment.digest(),
        repository_id=repository.id,
        issued_at=datetime.fromtimestamp(
            int(git_stdout(root, "show", "-s", "--format=%ct", head)), UTC
        ),
    )


def operation_projection(
    attestation: Attestation,
    statement: JsonObject,
    claim: JsonObject,
    result: JsonObject,
    freshness: JsonObject,
    before: object,
    output: JsonObject,
) -> JsonObject:
    """Project one validated native operation Attestation."""
    return {
        "predicate": attestation.predicate,
        "attestation_id": attestation.id,
        "commitment_digest": attestation.commitment_digest,
        "effect_digest": attestation.effect_digest,
        "repository": statement.get("repository"),
        "claim": claim,
        "result": result,
        "input": before,
        "output": output,
        "freshness": freshness,
    }


def recognized_operation_attestation(attestation: Attestation, predicate: str) -> bool:
    """Return whether one native operation Attestation is current and structurally valid."""
    now = datetime.now(UTC)
    return (
        attestation.verdict == "pass"
        and attestation.predicate == predicate
        and attestation.payload.kind == "effect:native"
        and attestation.verifier == "git"
        and (attestation.valid_from or attestation.issued_at) <= now
        and (attestation.valid_until is None or now <= attestation.valid_until)
        and attestation.commitment_digest is not None
        and attestation.effect_digest is not None
    )


def operation_effect_digest(
    attestation: Attestation,
    claim: JsonObject,
    freshness: JsonObject,
    before: object,
    output: JsonObject,
) -> str:
    """Return the canonical digest of one native operation effect."""
    return canonical_json_digest(
        {
            "predicate": attestation.predicate,
            "operation": claim.get("operation"),
            "command": attestation.payload.body.get("command"),
            "subject": freshness.get("subject"),
            "before": before,
            "after": output,
        }
    )


def semantic_mapping(value: object) -> JsonObject | None:
    """Normalize one semantic value to a JSON object when possible."""
    normalized = mutable_json(value)
    return normalized if isinstance(normalized, dict) else None


def _generation(value: object) -> JsonObject | None:
    normalized = mutable_json(value)
    if not isinstance(normalized, dict):
        return None
    payload = {"lane_ref": normalized.get("branch"), **normalized}
    payload.pop("branch", None)
    return normalized if mutable_json(lease_generation(payload)) == normalized else None


def prepare_start_effect(
    root: Path,
    *,
    change: str,
    previous_head: str,
    target_tree: str,
    current_lease: Mapping[str, object],
    commitment: Commitment,
    repository_id: str,
    command: tuple[str, ...],
    create: bool,
) -> dict[str, object]:
    """Persist or recognize one exact write-ahead start witness."""
    subject = {"change": change, "previous_head": previous_head, "tree": target_tree}
    candidates = tuple(
        item
        for item in read_attestation_set(root)[1]
        if item.predicate == "effect:openspec-change-start-prepared"
        and item.payload.body.get("freshness", {}).get("subject") == subject
    )
    if len(candidates) > 1:
        raise ValueError(_START_ATTESTATION_COLLISION)
    old = (
        lease_generation(dict(current_lease))
        if create
        else _prepared_old_generation(root, candidates, previous_head, current_lease)
    )
    effect = NativeEffect(
        predicate="effect:openspec-change-start-prepared",
        operation="openspec.change.start",
        command=command,
        subject=subject,
        before={"head": previous_head, "lease": old},
        after={
            "tree": target_tree,
            "commitment_path": f"openspec/changes/{change}/commitment.toml",
            "commitment_digest": commitment.digest(),
        },
    )
    expected = issue_native_effect(
        root,
        effect=effect,
        state="prepared",
        commitment_digest=commitment.digest(),
        repository_id=repository_id,
        issued_at=candidates[0].issued_at if candidates else datetime.now(UTC),
    )
    if candidates and candidates[0] != expected:
        raise ValueError(_START_ATTESTATION_COLLISION)
    if not candidates:
        if not create:
            raise ValueError(_START_ATTESTATION_MISSING)
        selected = record_attestation_once(root, expected)
        if selected != expected:
            retry = issue_native_effect(
                root,
                effect=effect,
                state="prepared",
                commitment_digest=commitment.digest(),
                repository_id=repository_id,
                issued_at=selected.issued_at,
            )
            if selected != retry:
                raise ValueError(_START_ATTESTATION_COLLISION)
    return old


def committed_start_attestation(
    root: Path,
    *,
    change: str,
    command: tuple[str, ...],
    previous_head: str,
    head: str,
    old_generation: Mapping[str, object],
    new_generation: Mapping[str, object],
    commitment: Commitment,
    repository_id: str,
) -> Attestation:
    """Return the unique committed start Attestation, recording it if absent."""
    subject = {"change": change, "previous_head": previous_head, "head": head}
    candidates = tuple(
        item
        for item in read_attestation_set(root)[1]
        if item.predicate == "effect:openspec-change-start"
        and item.payload.body.get("freshness", {}).get("subject") == subject
    )
    if len(candidates) > 1:
        raise ValueError(_START_ATTESTATION_COLLISION)
    expected = issue_native_effect(
        root,
        effect=NativeEffect(
            predicate="effect:openspec-change-start",
            operation="openspec.change.start",
            command=command,
            subject=subject,
            before={"head": previous_head, "lease": dict(old_generation)},
            after={"head": head, "lease": dict(new_generation)},
        ),
        state="prepared",
        commitment_digest=commitment.digest(),
        repository_id=repository_id,
        issued_at=datetime.fromtimestamp(
            int(git_stdout(root, "show", "-s", "--format=%ct", head)), UTC
        ),
    )
    if candidates and candidates[0] != expected:
        raise ValueError(_START_ATTESTATION_COLLISION)
    if not candidates:
        record_attestations(root, (expected,))
    return candidates[0] if candidates else expected


def recoverable_start_effect(
    root: Path,
    *,
    change: str,
    previous_head: str,
    lease: dict[str, object],
    command: tuple[str, ...],
) -> tuple[dict[str, object], tuple[str, ...]] | None:
    """Recognize a committed start awaiting Lease or Attestation completion."""
    head = current_tracked_head(root)
    carrier = f"openspec/changes/{change}/commitment.toml"
    if (
        head == previous_head
        or lease.get("lease_state") != "valid"
        or lease.get("holder_ref") != os.environ.get("ETHOS_ACTOR", "").strip()
        or lease.get("expected_head") not in {previous_head, head}
        or not str(lease.get("base_commitment_path") or "").startswith("openspec/changes/archive/")
        or git_stdout(root, "rev-parse", f"{head}^") != previous_head
        or git_stdout(root, "status", "--short")
    ):
        return None
    try:
        target = exact_commitment_fields(root, head=head, carrier=carrier, change_id=change)
        commitment = load_commitment(root, carrier=carrier, change_id=change, tree_ref=head)
        repository = load_repository_commitment(root, tree_ref=head)
    except ValueError:
        return None
    old = prepare_start_effect(
        root,
        change=change,
        previous_head=previous_head,
        target_tree=str(target["expected_tree"]),
        current_lease=lease,
        commitment=commitment,
        repository_id=repository.id,
        command=command,
        create=False,
    )
    return old, command


def recognized_start_effect(
    root: Path,
    *,
    change: str,
    previous_head: str,
    lease: dict[str, object],
) -> Attestation | None:
    """Return the unique authoritative Attestation for an already completed start."""
    head = current_tracked_head(root)
    carrier = f"openspec/changes/{change}/commitment.toml"
    if (
        lease.get("lease_state") != "valid"
        or lease.get("holder_ref") != os.environ.get("ETHOS_ACTOR", "").strip()
        or lease.get("expected_head") not in {previous_head, head}
        or lease.get("base_commitment_path") != carrier
        or git_stdout(root, "rev-parse", f"{head}^") != previous_head
    ):
        return None
    commitment = load_commitment(root, carrier=carrier, change_id=change, tree_ref=head)
    repository = load_repository_commitment(root, tree_ref=head)
    validated = [
        item
        for item in read_attestation_set(root)[1]
        if start_effect_authority(root, item, head, repository.id, commitment, lease)
    ]
    return validated[0] if len(validated) == 1 else None


def _prepared_old_generation(
    root: Path,
    candidates: tuple[Attestation, ...],
    previous_head: str,
    current_lease: Mapping[str, object],
) -> dict[str, object]:
    if len(candidates) != 1:
        raise ValueError(_START_ATTESTATION_MISSING)
    before = candidates[0].payload.body.get("input")
    old = before.get("lease") if isinstance(before, Mapping) else None
    normalized = mutable_json(old)
    if not isinstance(normalized, dict):
        raise TypeError(_START_ATTESTATION_COLLISION)
    current = lease_generation(dict(current_lease))
    mutable = {"expected_head", "expected_tree", "payload_sha256"}
    valid = (
        normalized.get("expected_head") == previous_head
        and normalized.get("expected_tree") == current_tree(root, previous_head)
        and {name: value for name, value in normalized.items() if name not in mutable}
        == {name: value for name, value in current.items() if name not in mutable}
        and current.get("expected_head") in {previous_head, current_tracked_head(root)}
        and current.get("expected_tree") == current_tree(root, str(current.get("expected_head")))
    )
    if not valid:
        raise ValueError(_START_ATTESTATION_COLLISION)
    return normalized


def lease_binding(value: object) -> dict[str, object]:
    """Project only the Lease fields carried by lifecycle Attestations."""
    lease = dict(value) if isinstance(value, dict) else {}
    return {
        name: lease.get(name)
        for name in (
            "lease_id",
            "lane_incarnation_id",
            "lane_ref",
            "holder_ref",
            "expected_head",
            "expected_tree",
            "base_commitment_path",
            "base_commitment_bytes_sha256",
            "base_commitment_digest",
        )
    }


def exact_archive_paths(root: Path, head: str, archive_path: str, paths: tuple[str, ...]) -> bool:
    """Recognize the exact archive-only path set for one commit."""
    parent = git_stdout(root, "rev-parse", f"{head}^")
    actual = tuple(
        git_stdout(root, "diff", "--name-only", "--diff-filter=ACMRTD", parent, head).splitlines()
    )
    return (
        archive_path.startswith("openspec/changes/archive/")
        and bool(parent and actual)
        and actual == paths
        and all(path.startswith((f"{archive_path}/", "openspec/specs/")) for path in paths)
    )
