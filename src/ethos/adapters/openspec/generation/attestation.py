"""Validate exact OpenSpec start and archive effect attestations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import current_tree, git_stdout, is_ancestor
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import integer, string_sequence

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation, Commitment
    from ethos.contracts.value import JsonObject


def start_effect_authority(
    root: Path,
    attestation: Attestation,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
) -> JsonObject:
    if not _recognized_operation_attestation(
        attestation, "effect:openspec-change-start"
    ):
        return {}
    statement = attestation.payload.body
    values = tuple(
        _mapping(statement.get(name))
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
        started = (
            load_lease_bound_commitment(root, lease=new, change_id=change)
            if new
            else None
        )
    except ValueError:
        started = None
    valid = (
        attestation.verdict == "pass"
        and started is not None
        and started.digest() == commitment.digest()
        and attestation.commitment_digest == started.digest()
        and statement.get("repository") == repository_id
        and claim
        == {"operation": "openspec.change.start", "effect": attestation.effect_digest}
        and result == {"state": "applied", "executed": True, "exit_code": 0}
        and old is not None
        and new is not None
        and new.get("branch") == current.get("branch")
        and new.get("lane_incarnation_id") == current.get("lane_incarnation_id")
        and new.get("lease_id") == current.get("lease_id")
        and integer(new.get("epoch"), default=-1)
        <= integer(current.get("epoch"), default=-1)
        and new.get("expected_head") == start_head
        and new.get("expected_tree") == current_tree(root, start_head)
        and current.get("expected_head") == head
        and current.get("expected_tree") == current_tree(root, head)
        and current.get("base_commitment_path")
        == f"openspec/changes/{change}/commitment.toml"
        and old.get("expected_head") == previous_head
        and old.get("expected_tree") == current_tree(root, previous_head)
        and commitment.predecessors == (old.get("base_commitment_digest"),)
        and all(
            old.get(name) == new.get(name)
            for name in ("branch", "lane_incarnation_id", "lease_id", "holder_ref")
        )
        and old.get("epoch") == new.get("epoch", 0) - 1
        and str(old.get("base_commitment_path") or "").startswith(
            "openspec/changes/archive/"
        )
        and new.get("base_commitment_path")
        == f"openspec/changes/{change}/commitment.toml"
        and git_stdout(root, "rev-parse", f"{start_head}^") == previous_head
        and is_ancestor(root, start_head, head)
        and freshness.get("repository") == repository_id
        and freshness.get("subject")
        == {"change": change, "previous_head": previous_head, "head": start_head}
        and freshness.get("change") == change
        and freshness.get("previous_head") == previous_head
        and freshness.get("head") == start_head
        and freshness.get("output_digest") == canonical_json_digest(output)
        and statement.get("input_digest") == canonical_json_digest(before)
        and statement.get("output_digest")
        == canonical_json_digest({"result": result, "output": output})
        and attestation.effect_digest
        == _effect_digest(attestation, claim, freshness, before, output)
    )
    return (
        _projection(attestation, statement, claim, result, freshness, before, output)
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
    if not _recognized_operation_attestation(attestation, "effect:openspec-archive"):
        return {}
    statement = attestation.payload.body
    output, claim, result, freshness = (
        _mapping(statement.get(name))
        for name in ("output", "claim", "result", "freshness")
    )
    if None in (output, claim, result, freshness):
        return {}
    output, claim, result, freshness = cast(
        "tuple[JsonObject, JsonObject, JsonObject, JsonObject]",
        (output, claim, result, freshness),
    )
    archive_path = str(output.get("archive_path") or "")
    paths = tuple(string_sequence(output.get("changed_paths")))
    before = statement.get("input")
    valid = (
        attestation.verdict == "pass"
        and attestation.commitment_digest == commitment.digest()
        and statement.get("repository") == repository_id
        and claim
        == {"operation": "openspec.archive", "effect": attestation.effect_digest}
        and result == {"state": "applied", "executed": True, "exit_code": 0}
        and output.get("head") == head
        and output.get("tree") == current_tree(root, head)
        and _lease_binding(output.get("lease")) == _lease_binding(lease)
        and freshness.get("repository") == repository_id
        and freshness.get("archive_path") == archive_path
        and freshness.get("output_digest") == canonical_json_digest(output)
        and statement.get("input_digest") == canonical_json_digest(before)
        and statement.get("output_digest")
        == canonical_json_digest({"result": result, "output": output})
        and attestation.effect_digest
        == _effect_digest(attestation, claim, freshness, before, output)
        and _exact_archive_paths(root, head, archive_path, paths)
    )
    return (
        _projection(attestation, statement, claim, result, freshness, before, output)
        | {"authorized_paths": list(paths)}
        if valid
        else {}
    )


def _projection(
    attestation: Attestation,
    statement: JsonObject,
    claim: JsonObject,
    result: JsonObject,
    freshness: JsonObject,
    before: object,
    output: JsonObject,
) -> JsonObject:
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


def _recognized_operation_attestation(attestation: Attestation, predicate: str) -> bool:
    now = datetime.now(UTC)
    return (
        attestation.predicate == predicate
        and attestation.payload.kind == "effect:native"
        and attestation.verifier == "git"
        and (attestation.valid_from or attestation.issued_at) <= now
        and (attestation.valid_until is None or now <= attestation.valid_until)
        and attestation.commitment_digest is not None
        and attestation.effect_digest is not None
    )


def _effect_digest(
    attestation: Attestation,
    claim: JsonObject,
    freshness: JsonObject,
    before: object,
    output: JsonObject,
) -> str:
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


def _mapping(value: object) -> JsonObject | None:
    normalized = mutable_json(value)
    return normalized if isinstance(normalized, dict) else None


def _generation(value: object) -> JsonObject | None:
    normalized = _mapping(value)
    if normalized is None:
        return None
    expected = lease_generation(
        {
            "lane_ref": normalized.get("branch"),
            **{name: normalized.get(name) for name in normalized if name != "branch"},
        }
    )
    return normalized if mutable_json(expected) == normalized else None


def _lease_binding(value: object) -> dict[str, object]:
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


def _exact_archive_paths(
    root: Path, head: str, archive_path: str, paths: tuple[str, ...]
) -> bool:
    parent = git_stdout(root, "rev-parse", f"{head}^")
    actual = tuple(
        git_stdout(
            root, "diff", "--name-only", "--diff-filter=ACMRTD", parent, head
        ).splitlines()
    )
    return (
        archive_path.startswith("openspec/changes/archive/")
        and bool(parent and actual)
        and actual == paths
        and all(
            path.startswith((f"{archive_path}/", "openspec/specs/")) for path in paths
        )
    )
