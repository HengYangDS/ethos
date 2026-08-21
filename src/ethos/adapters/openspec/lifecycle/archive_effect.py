"""Own exact prepared and terminal OpenSpec archive effect identity."""

from __future__ import annotations

import json
import os
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import NamedTuple

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.generation.attestation import lease_binding
from ethos.adapters.openspec.lifecycle.archive_binding import archive_context
from ethos.adapters.openspec.lifecycle.archive_transition import archive_postimage_scope_report
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.native_effect_attestation import native_effect_components
from ethos.adapters.repo.native_effect_attestation import native_effect_digest
from ethos.adapters.repo.native_effect_attestation import native_effect_projection
from ethos.adapters.repo.native_effect_attestation import native_effect_result
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.worktree_postimage import observe_worktree_postimage
from ethos.contracts.semantic import canonical_json_digest
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.semantic import Attestation
    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject

_ENVIRONMENT = "ETHOS_ARCHIVE_TRANSITION"
_FIELDS = frozenset(
    {
        "schema_version",
        "change",
        "head",
        "head_tree",
        "index_tree",
        "changed_paths",
        "completion_artifacts",
        "official_change_complete",
        "effect_identity",
    }
)


class ArchiveTransition(NamedTuple):
    """Typed exact archive transition carried across the hook boundary."""

    change: str
    head: str
    tree: str
    changed_paths: tuple[str, ...]
    completion_artifacts: tuple[str, ...]
    effect_identity: str


class PreparedArchiveAuthority(NamedTuple):
    """Minimal exact authority shared by write and ref-CAS admission."""

    head: str
    effect_identity: str
    branch: str
    holder: str
    actor: str
    generation: Mapping[str, object]
    commitment: Commitment
    material_scope: Mapping[str, object]


class ArchivePostimage(NamedTuple):
    """One exact official archive post-image observed from the worktree."""

    change: str
    head: str
    scope: Mapping[str, object] | None
    active_present: bool


class ArchivePrewriteRecovery(NamedTuple):
    """One exact non-authorizing continuation for an ownerless archive post-image."""

    change: str
    expected_head: str
    material_scope: Mapping[str, object]


def archive_effect_identity(
    root: Path,
    *,
    change: str,
    head: str,
    tree: str,
    changed_paths: tuple[str, ...],
) -> str:
    """Identify one archive effect from immutable Git coordinates."""
    return canonical_json_digest(
        {
            "operation": "openspec.archive",
            "change": change,
            "head": head,
            "head_tree": current_tree(root, head),
            "result_tree": tree,
            "changed_paths": list(changed_paths),
        }
    )


def archive_transition_environment(
    root: Path,
    *,
    change: str,
    head: str,
    changed_paths: tuple[str, ...],
    official_change_complete: bool,
    completion_artifacts: tuple[str, ...],
) -> dict[str, str]:
    """Bind a hook invocation to the exact admitted official archive delta."""
    tree = run_git(root, "write-tree").stdout.strip()
    payload: dict[str, object] = {
        "schema_version": 1,
        "change": change,
        "head": head,
        "head_tree": current_tree(root, head),
        "index_tree": tree,
        "changed_paths": list(changed_paths),
        "completion_artifacts": list(completion_artifacts),
        "official_change_complete": official_change_complete,
        "effect_identity": archive_effect_identity(
            root,
            change=change,
            head=head,
            tree=tree,
            changed_paths=changed_paths,
        ),
    }
    return {_ENVIRONMENT: json.dumps(payload, sort_keys=True, separators=(",", ":"))}


def archive_transition_facts(
    root: Path,
    *,
    changed_paths: tuple[str, ...],
    requested_change: str | None,
) -> tuple[bool, tuple[str, ...]] | None:
    """Read exact process-local archive facts for their bound staged tree."""
    transition = _transition(
        root,
        head=current_tracked_head(root),
        tree=run_git(root, "write-tree").stdout.strip(),
        changed_paths=changed_paths,
    )
    if transition is None or requested_change not in {None, transition.change}:
        return None
    return True, transition.completion_artifacts


def archive_prewrite_authority(
    root: Path,
    *,
    changed_paths: tuple[str, ...],
    branch: str,
    actor: str,
) -> dict[str, object] | None:
    """Project one exact prepared archive effect as tracked-write authority."""
    authority = _prepared_archive_authority(
        root,
        head=current_tracked_head(root),
        tree=run_git(root, "write-tree").stdout.strip(),
        changed_paths=changed_paths,
        branch=branch,
        actor=actor,
    )
    if authority is None:
        return None
    return {
        "verdict": "pass",
        "required": True,
        "authority_kind": "prepared_effect",
        "branch": authority.branch,
        "holder_ref": authority.holder,
        "invocation_holder_ref": authority.actor,
        "lease_id": str(authority.generation.get("lease_id") or ""),
        "epoch": authority.generation.get("epoch", 0),
        "expected_head": authority.head,
        "base_commitment_digest": authority.commitment.digest(),
        "effect_identity": authority.effect_identity,
        "material_scope": dict(authority.material_scope),
        "reason": "exact_prepared_archive_effect",
    }


def archive_prewrite_recovery(
    root: Path,
    *,
    changed_paths: tuple[str, ...],
    branch: str,
) -> ArchivePrewriteRecovery | None:
    """Recognize an exact ownerless post-image without authorizing a bare commit."""
    if not any(path.startswith("openspec/changes/archive/") for path in changed_paths):
        return None
    context = archive_context(root)
    if context is None:
        return None
    head, generation, commitment = context
    lane = str(generation.get("lane_ref") or generation.get("branch") or "")
    if generation.get("lease_state") != "ownerless_recovery" or lane != branch:
        return None
    postimage = archive_postimage(root, head=head, change=commitment.id.removeprefix("change:"))
    if (
        postimage is None
        or postimage.active_present
        or postimage.scope is None
        or postimage.scope.get("verdict") != "pass"
    ):
        return None
    return ArchivePrewriteRecovery(postimage.change, postimage.head, postimage.scope)


def archive_postimage(root: Path, *, head: str, change: str) -> ArchivePostimage | None:
    """Select the exact official post-image shared by command and remediation paths."""
    if not change:
        return None
    active = f"openspec/changes/{change}/commitment.toml"
    with observe_worktree_postimage(root, previous=head) as observed:
        active_present = (
            run_git(
                root,
                "rev-parse",
                f"{observed.tree}:{active}",
                check=False,
                env=observed.environment,
            ).returncode
            == 0
        )
        if observed.tree == current_tree(root, head):
            return ArchivePostimage(change, head, None, active_present)
        scope = archive_postimage_scope_report(
            root,
            changed_paths=observed.changed_paths,
            requested_change=change,
            tree=observed.tree,
            environment=observed.environment,
        )
    return ArchivePostimage(change, head, scope, active_present)


def prepared_archive_ref_authority(
    root: Path,
    *,
    branch: str,
    old_value: str,
    new_value: str,
    actor: str,
) -> dict[str, object] | None:
    """Validate one exact prepared archive commit before its ref CAS."""
    if git_stdout(root, "rev-list", "--parents", "-n", "1", new_value).split() != [
        new_value,
        old_value,
    ]:
        return None
    authority = _prepared_archive_authority(
        root,
        head=old_value,
        tree=current_tree(root, new_value),
        changed_paths=_changed_paths(root, old_value, new_value),
        branch=branch,
        actor=actor,
    )
    if authority is None:
        return None
    return {
        "authority_kind": "prepared_effect",
        "effect_identity": authority.effect_identity,
        "holder_ref": authority.holder,
        "branch": authority.branch,
        "expected_head": authority.head,
        "desired_head": new_value,
    }


def lease_bound_archive_transition_fields(
    root: Path,
    *,
    target_head: str,
) -> dict[str, str] | None:
    """Return the exact prepared archive target bound to one effect identity."""
    branch = git_stdout(root, "branch", "--show-current")
    lease = leases_by_branch(root).get(branch, {})
    old_head = str(lease.get("expected_head") or "")
    if lease.get("lease_state") != "valid" or not old_head:
        return None
    try:
        source = load_lease_bound_commitment(root, lease=lease)
        change = source.id.removeprefix("change:")
        tree = current_tree(root, target_head)
        paths = _changed_paths(root, old_head, target_head)
        transition = _transition(root, head=old_head, tree=tree, changed_paths=paths)
        scope = (
            archive_postimage_scope_report(
                root,
                changed_paths=paths,
                requested_change=change,
                tree=tree,
                source_head=old_head,
            )
            if transition is not None and transition.change == change
            else None
        )
        archive_path = scope.get("archive_path") if scope is not None else None
        if scope is None or scope.get("verdict") != "pass" or not archive_path:
            return None
        return exact_commitment_fields(
            root,
            head=target_head,
            carrier=f"{archive_path}/commitment.toml",
            change_id=change,
        )
    except ValueError:
        return None


def archive_effect_authority(
    root: Path,
    attestation: Attestation,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
) -> JsonObject:
    """Project exact archive authority from one valid Attestation."""
    components = native_effect_components(attestation, "effect:openspec-archive")
    if components is None:
        return {}
    statement, before, output, claim, result, freshness = components
    previous_head = str(before.get("head") or "")
    archive_path = str(output.get("archive_path") or "")
    paths = tuple(string_sequence(output.get("changed_paths")))
    valid = (
        attestation.commitment_digest == commitment.digest()
        and statement.get("repository") == repository_id
        and claim == {"operation": "openspec.archive", "effect": attestation.effect_digest}
        and result == native_effect_result("applied")
        and output.get("head") == head
        and output.get("tree") == current_tree(root, head)
        and lease_binding(output.get("lease")) == lease_binding(lease)
        and before.get("effect_identity")
        == archive_effect_identity(
            root,
            change=commitment.id.removeprefix("change:"),
            head=previous_head,
            tree=str(output.get("tree") or ""),
            changed_paths=paths,
        )
        and freshness.get("output_digest") == canonical_json_digest(output)
        and statement.get("input_digest") == canonical_json_digest(before)
        and statement.get("output_digest")
        == canonical_json_digest({"result": result, "output": output})
        and attestation.effect_digest
        == native_effect_digest(attestation, claim, freshness, before, output)
        and exact_archive_paths(root, head, archive_path, paths)
    )
    return (
        native_effect_projection(attestation, statement, claim, result, freshness, before, output)
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
                "effect_identity": archive_effect_identity(
                    root,
                    change=change,
                    head=previous_head,
                    tree=current_tree(root, head),
                    changed_paths=changed_paths,
                ),
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


def _changed_paths(root: Path, old_head: str, new_head: str) -> tuple[str, ...]:
    return tuple(
        filter(
            None,
            git_stdout(root, "diff", "--name-only", f"{old_head}..{new_head}").splitlines(),
        )
    )


def _transition(
    root: Path,
    *,
    head: str,
    tree: str,
    changed_paths: tuple[str, ...],
) -> ArchiveTransition | None:
    try:
        payload = json.loads(os.environ.get(_ENVIRONMENT, ""))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or set(payload) != _FIELDS:
        return None
    change = payload.get("change")
    artifacts = payload.get("completion_artifacts")
    effect_identity = payload.get("effect_identity")
    if not (
        payload.get("schema_version") == 1
        and isinstance(change, str)
        and bool(change)
        and payload.get("head") == head
        and payload.get("head_tree") == current_tree(root, head)
        and payload.get("index_tree") == tree
        and payload.get("changed_paths") == list(changed_paths)
        and isinstance(artifacts, list)
        and all(isinstance(path, str) and path for path in artifacts)
        and payload.get("official_change_complete") is True
        and isinstance(effect_identity, str)
        and effect_identity
        == archive_effect_identity(
            root,
            change=change,
            head=head,
            tree=tree,
            changed_paths=changed_paths,
        )
    ):
        return None
    return ArchiveTransition(
        change,
        head,
        tree,
        changed_paths,
        tuple(artifacts),
        effect_identity,
    )


def _prepared_archive_authority(
    root: Path,
    *,
    head: str,
    tree: str,
    changed_paths: tuple[str, ...],
    branch: str,
    actor: str,
) -> PreparedArchiveAuthority | None:
    transition = _transition(root, head=head, tree=tree, changed_paths=changed_paths)
    context = archive_context(root)
    if transition is None or context is None:
        return None
    context_head, generation, commitment = context
    holder = str(generation.get("holder_ref") or "")
    lane = str(generation.get("lane_ref") or generation.get("branch") or "")
    scope = archive_postimage_scope_report(
        root,
        changed_paths=changed_paths,
        requested_change=transition.change,
        tree=tree,
    )
    if (
        context_head != head
        or lane != branch
        or not actor
        or actor != holder
        or commitment.id != f"change:{transition.change}"
        or scope is None
        or scope.get("verdict") != "pass"
    ):
        return None
    return PreparedArchiveAuthority(
        head,
        transition.effect_identity,
        branch,
        holder,
        actor,
        generation,
        commitment,
        scope,
    )
