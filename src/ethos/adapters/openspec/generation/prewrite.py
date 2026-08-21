"""Project exact prepared Change-start effects as tracked-write authority."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from ethos.adapters.openspec.generation.attestation import prepare_start_effect
from ethos.adapters.openspec.lifecycle.scope import prepared_change_scope_report
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path


def prepared_start_prewrite_authority(
    root: Path,
    *,
    changed_paths: tuple[str, ...],
    branch: str,
    actor: str,
) -> dict[str, object] | None:
    """Project one exact prepared Change start as tracked-write authority."""
    lease = leases_by_branch(root).get(branch, {})
    head, tree = current_tracked_head(root), git_stdout(root, "write-tree")
    paths = tuple(dict.fromkeys(changed_paths))
    candidates = tuple(
        item
        for item in read_attestation_set(root)[1]
        if item.predicate == "effect:openspec-change-start-prepared"
        and item.payload.body.get("freshness", {}).get("subject", {}).get("tree") == tree
    )
    attestation = candidates[0] if len(candidates) == 1 else None
    body = attestation.payload.body if attestation is not None else {}
    freshness, before, output = body.get("freshness"), body.get("input"), body.get("output")
    subject = freshness.get("subject") if isinstance(freshness, Mapping) else None
    change = subject.get("change") if isinstance(subject, Mapping) else None
    carrier = output.get("commitment_path") if isinstance(output, Mapping) else None
    if not (
        attestation is not None
        and isinstance(subject, Mapping)
        and isinstance(before, Mapping)
        and isinstance(output, Mapping)
        and isinstance(change, str)
        and isinstance(carrier, str)
    ):
        return None
    try:
        commitment = load_commitment(root, carrier=carrier, change_id=change, tree_ref=tree)
        repository = load_repository_commitment(root, tree_ref=tree)
        expected = prepare_start_effect(
            root,
            change=change,
            previous_head=head,
            target_tree=tree,
            current_lease=lease,
            commitment=commitment,
            repository_id=repository.id,
            command=tuple(string_sequence(body.get("command"), drop_empty=True)),
            create=False,
        )
    except (TypeError, ValueError):
        return None
    delta = tuple(
        filter(
            None,
            git_stdout(
                root, "diff-tree", "--no-commit-id", "--name-only", "-r", head, tree
            ).splitlines(),
        )
    )
    scope = prepared_change_scope_report(
        root,
        changed_paths=paths,
        change=change,
        commitment=commitment,
    )
    if not (
        subject == {"change": change, "previous_head": head, "tree": tree}
        and set(paths) == set(delta)
        and carrier == f"openspec/changes/{change}/commitment.toml"
        and output.get("tree") == tree
        and output.get("commitment_digest") == commitment.digest()
        and before.get("head") == head
        and mutable_json(before.get("lease")) == expected
        and lease_generation(lease) == expected
        and expected.get("branch") == branch
        and expected.get("holder_ref") == actor
        and bool(actor)
        and scope.get("verdict") == "pass"
        and scope.get("state") == "change_start_transition"
    ):
        return None
    return {
        "verdict": "pass",
        "required": True,
        "authority_kind": "prepared_effect",
        "branch": branch,
        "holder_ref": actor,
        "invocation_holder_ref": actor,
        "lease_id": str(expected.get("lease_id") or ""),
        "epoch": expected.get("epoch", 0),
        "expected_head": head,
        "base_commitment_digest": str(expected.get("base_commitment_digest") or ""),
        "effect_identity": attestation.effect_digest or "",
        "material_scope": scope,
        "reason": "exact_prepared_start_effect",
    }
