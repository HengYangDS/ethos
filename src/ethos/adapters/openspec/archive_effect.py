"""Resolve exact post-archive scope authority from local effect evidence."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof_artifacts import attestation_store_dir
from ethos.adapters.mutation.proof_artifacts import scan_attestations
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import repository_path_matches
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation
    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject


def archive_effect_authority(
    root: Path,
    *,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
    changed_paths: tuple[str, ...],
) -> JsonObject:
    """Return the sole exact archive effect that authorizes current paths."""
    authority = archive_generation_authority(
        root,
        head=head,
        repository_id=repository_id,
        commitment=commitment,
        lease=lease,
    )
    if not authority:
        return {}
    authority_paths = tuple(string_sequence(authority.get("authorized_paths")))
    outside_commitment = tuple(
        path
        for path in changed_paths
        if not any(repository_path_matches(path, pattern) for pattern in commitment.scope)
    )
    return authority if set(outside_commitment).issubset(authority_paths) else {}


def archive_generation_authority(
    root: Path,
    *,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
) -> JsonObject:
    """Return the sole exact archive transition that produced the current HEAD."""
    matches = tuple(
        projection
        for attestation in scan_attestations(attestation_store_dir(root))[0]
        if (
            projection := _archive_projection(
                root,
                attestation=attestation,
                head=head,
                repository_id=repository_id,
                commitment=commitment,
                lease=lease,
            )
        )
    )
    return matches[0] if len(matches) == 1 else {}


def _archive_projection(
    root: Path,
    *,
    attestation: Attestation,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
) -> JsonObject:
    statement = attestation.statement
    output = statement.get("output")
    claim = statement.get("claim")
    result = statement.get("result")
    freshness = statement.get("freshness")
    if not all(isinstance(item, Mapping) for item in (output, claim, result, freshness)):
        return {}
    normalized = tuple(mutable_json(item) for item in (output, claim, result, freshness))
    if not all(isinstance(item, dict) for item in normalized):
        return {}
    output, claim, result, freshness = (
        {str(key): value for key, value in item.items()}
        for item in normalized
        if isinstance(item, dict)
    )
    authority_paths = tuple(string_sequence(output.get("changed_paths")))
    archive_path = str(output.get("archive_path") or "")
    effect = {
        "predicate": attestation.predicate,
        "attestation_id": attestation.id,
        "commitment_digest": attestation.commitment_digest,
        "effect_digest": attestation.effect_digest,
        "repository": statement.get("repository"),
        "claim": claim,
        "result": result,
        "input": statement.get("input"),
        "output": output,
        "freshness": freshness,
    }
    valid = (
        attestation.predicate == "effect:openspec-archive"
        and attestation.verdict == "pass"
        and attestation.commitment_digest == commitment.digest()
        and statement.get("repository") == repository_id
        and claim.get("operation") == "openspec.archive"
        and claim.get("effect") == attestation.effect_digest
        and result == {"state": "applied", "executed": True, "exit_code": 0}
        and output.get("head") == head
        and output.get("tree") == current_tree(root, head)
        and _lease_binding(output.get("lease")) == _lease_binding(lease)
        and freshness.get("repository") == repository_id
        and freshness.get("archive_path") == archive_path
        and freshness.get("output_digest") == canonical_json_digest(output)
        and statement.get("input_digest") == canonical_json_digest(statement.get("input"))
        and statement.get("output_digest")
        == canonical_json_digest({"result": result, "output": output})
        and attestation.effect_digest
        == canonical_json_digest(
            {
                "predicate": attestation.predicate,
                "operation": claim.get("operation"),
                "command": statement.get("command"),
                "subject": freshness.get("subject"),
                "before": statement.get("input"),
                "after": output,
            }
        )
        and _archive_paths_are_exact(root, head, archive_path, authority_paths)
    )
    return effect | {"authorized_paths": list(authority_paths)} if valid else {}


def _lease_binding(value: object) -> dict[str, object]:
    lease = dict(value) if isinstance(value, Mapping) else {}
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


def _archive_paths_are_exact(
    root: Path,
    head: str,
    archive_path: str,
    authority_paths: tuple[str, ...],
) -> bool:
    if not archive_path or PurePosixPath(archive_path).parts[:3] != (
        "openspec",
        "changes",
        "archive",
    ):
        return False
    parent = git_stdout(root, "rev-parse", f"{head}^")
    actual = tuple(
        git_stdout(
            root,
            "diff",
            "--name-only",
            "--diff-filter=ACMRTD",
            parent,
            head,
        ).splitlines()
    )
    return (
        bool(parent and actual)
        and actual == authority_paths
        and all(
            path.startswith((f"{archive_path}/", "openspec/specs/")) for path in authority_paths
        )
    )
