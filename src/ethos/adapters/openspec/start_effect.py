"""Resolve one current OpenSpec Change generation from exact start evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.mutation.proof_artifacts import attestation_store_dir
from ethos.adapters.mutation.proof_artifacts import scan_attestations
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import repository_path_matches

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation
    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject


@dataclass(frozen=True, slots=True)
class CurrentGenerationScope:
    """One current Change generation scope and its exact start receipt."""

    paths: tuple[str, ...]
    start_authority: JsonObject


def current_generation_scope(
    root: Path,
    *,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
    fallback_paths: tuple[str, ...],
) -> CurrentGenerationScope:
    """Prefer the sole exact current start generation over the candidate baseline."""
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
    if len(matches) != 1:
        return CurrentGenerationScope(fallback_paths, {})
    authority = matches[0]
    previous_head = str(authority["previous_head"])
    paths = git_stdout(root, "diff", "--name-only", f"{previous_head}...{head}").splitlines()
    return CurrentGenerationScope(tuple(dict.fromkeys((*paths, *changed_paths(root)))), authority)


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
    change = commitment.id.removeprefix("change:")
    before, after = _generation(input_data.get("lease")), _generation(output.get("lease"))
    actual_paths = tuple(
        git_stdout(root, "diff", "--name-only", f"{previous_head}...{head}").splitlines()
    )
    valid = (
        attestation.predicate == "effect:openspec-change-start"
        and attestation.verdict == "pass"
        and attestation.commitment_digest == commitment.digest()
        and statement.get("repository") == repository_id
        and claim == {"operation": "openspec.change.start", "effect": attestation.effect_digest}
        and result == {"state": "applied", "executed": True, "exit_code": 0}
        and output.get("head") == head
        and before is not None
        and after is not None
        and after == lease_generation(lease)
        and before.get("expected_head") == previous_head
        and before.get("expected_tree") == current_tree(root, previous_head)
        and before.get("branch") == after.get("branch")
        and before.get("lane_incarnation_id") == after.get("lane_incarnation_id")
        and before.get("lease_id") == after.get("lease_id")
        and before.get("holder_ref") == after.get("holder_ref")
        and before.get("epoch") == after.get("epoch", 0) - 1
        and str(before.get("base_commitment_path") or "").startswith("openspec/changes/archive/")
        and after.get("base_commitment_path") == f"openspec/changes/{change}/commitment.toml"
        and current_tree(root, head) == str(after.get("expected_tree") or "")
        and git_stdout(root, "rev-parse", f"{head}^") == previous_head
        and freshness.get("repository") == repository_id
        and freshness.get("subject")
        == {"change": change, "previous_head": previous_head, "head": head}
        and freshness.get("change") == change
        and freshness.get("previous_head") == previous_head
        and freshness.get("head") == head
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
        and bool(actual_paths)
        and all(
            any(repository_path_matches(path, pattern) for pattern in commitment.scope)
            for path in actual_paths
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
