"""Strict authority for pre-protocol active and archive-reactivated generations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.git import committed_file_bytes
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.semantic import canonical_json_digest
from ethos.normalization.coercion import repository_path_matches

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject


def exact_initial_active_generation(
    root: Path,
    *,
    head: str,
    commitment: Commitment,
    carrier: str,
    fallback_paths: tuple[str, ...],
) -> bool:
    """Admit one active carrier created directly from a configured integration root."""
    policy = load_branch_role_policy(root)
    bases = tuple(
        base
        for branch in (policy.candidate_branch, policy.accepted_branch)
        if (base := git_stdout(root, "rev-parse", "--verify", branch))
        and is_ancestor(root, base, head)
    )
    if not bases or not carrier or not fallback_paths:
        return False
    base = min(
        bases,
        key=lambda candidate: len(
            git_stdout(root, "rev-list", f"{candidate}..{head}").splitlines()
        ),
    )
    return (
        carrier.startswith("openspec/changes/")
        and not carrier.startswith("openspec/changes/archive/")
        and not committed_file_bytes(root, base, carrier)
        and bool(committed_file_bytes(root, head, carrier))
        and not archived_commitment_carriers(
            root,
            head=base,
            change=commitment.id.removeprefix("change:"),
        )
        and all(
            any(repository_path_matches(path, pattern) for pattern in commitment.scope)
            for path in fallback_paths
        )
    )


def archive_reactivation_authority(
    root: Path,
    *,
    head: str,
    commitment: Commitment,
    carrier: str,
) -> JsonObject:
    """Recognize one exact accepted archive restored by the first lane commit."""
    policy = load_branch_role_policy(root)
    role_heads = tuple(
        candidate_head
        for branch in (policy.candidate_branch, policy.accepted_branch)
        if (candidate_head := git_stdout(root, "rev-parse", "--verify", branch))
        and is_ancestor(root, candidate_head, head)
    )
    role_commits = tuple(
        (candidate_head, commits)
        for candidate_head in role_heads
        if (
            commits := git_stdout(
                root, "rev-list", "--reverse", f"{candidate_head}..{head}"
            ).splitlines()
        )
    )
    if not role_commits:
        return {}
    generation_base, commits = min(role_commits, key=lambda item: len(item[1]))
    restored_head = commits[0]
    if git_stdout(root, "rev-parse", f"{restored_head}^") != generation_base:
        return {}
    change = commitment.id.removeprefix("change:")
    candidates = archived_commitment_carriers(root, head=generation_base, change=change)
    if len(candidates) != 1:
        return {}
    source = candidates[0]
    source_prefix = source.removesuffix("commitment.toml")
    target_prefix = carrier.removesuffix("commitment.toml")
    carrier_transitioned = not (
        not carrier
        or committed_file_bytes(root, generation_base, carrier)
        or committed_file_bytes(root, restored_head, source)
        or not committed_file_bytes(root, restored_head, carrier)
    )
    if not (
        carrier_transitioned
        and _has_stable_archive_relocation(
            root,
            candidate_head=generation_base,
            restored_head=restored_head,
            source_prefix=source_prefix,
            target_prefix=target_prefix,
        )
    ):
        return {}
    return {
        "predicate": "effect:openspec-archive-reactivation",
        "attestation_id": canonical_json_digest(
            {
                "generation_base": generation_base,
                "restored_head": restored_head,
                "source": source,
                "target": carrier,
            }
        ),
        "previous_head": generation_base,
        "restored_head": restored_head,
        "source_carrier": source,
        "source_prefix": source_prefix,
        "target_carrier": carrier,
    }


def archived_commitment_carriers(root: Path, *, head: str, change: str) -> tuple[str, ...]:
    """Return archived carriers at one tree whose Commitment has the exact identity."""
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


def _has_stable_archive_relocation(
    root: Path,
    *,
    candidate_head: str,
    restored_head: str,
    source_prefix: str,
    target_prefix: str,
) -> bool:
    """Prove the first lane commit removed the archive and restored stable bytes."""
    source_paths = tuple(
        path
        for path in git_stdout(root, "ls-tree", "-r", "--name-only", candidate_head).splitlines()
        if path.startswith(source_prefix)
    )
    if any(committed_file_bytes(root, restored_head, path) for path in source_paths):
        return False
    stable_paths = tuple(
        path for path in source_paths if path.endswith("/.openspec.yaml") or "/specs/" in path
    )
    return any(
        committed_file_bytes(root, candidate_head, source_path)
        == committed_file_bytes(
            root,
            restored_head,
            f"{target_prefix}{source_path.removeprefix(source_prefix)}",
        )
        != b""
        for source_path in stable_paths
    )
