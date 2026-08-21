"""Resolve exact Lease-bound OpenSpec archive carrier transitions."""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Mapping
from datetime import date
from typing import TYPE_CHECKING

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.commitment import commitment_binding_mismatch
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import validate as validate_git_effect_attestation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Commitment

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

ARCHIVE_COMMITMENT = re.compile(
    r"^openspec/changes/archive/(20\d{2}-\d{2}-\d{2})-"
    r"([a-z][a-z0-9]*(?:-[a-z0-9]+)*)/commitment\.toml$"
)
ACTIVE_COMMITMENT = re.compile(
    r"^openspec/changes/([a-z][a-z0-9]*(?:-[a-z0-9]+)*)/commitment\.toml$"
)


def archive_context(
    root: Path,
    *,
    source_head: str | None = None,
) -> tuple[str, dict[str, object], Commitment] | None:
    """Return one exact live or ownerless Work Lane archive context."""
    branch = git_stdout(root, "branch", "--show-current")
    if load_branch_role_policy(root).role_for_branch(branch) != ROLE_WORK_LANE:
        return None
    head = source_head or git_stdout(root, "rev-parse", "HEAD")
    lease = leases_by_branch(root).get(branch, {})
    if (
        lease.get("lease_state") == "valid"
        and lease.get("commitment_binding") == "bound"
        and lease.get("expected_head") == head
    ):
        try:
            return head, lease, load_lease_bound_commitment(root, lease=lease)
        except ValueError:
            return None
    return _ownerless_archive_context(root, branch=branch, head=head)


def _ownerless_archive_context(
    root: Path,
    *,
    branch: str,
    head: str,
) -> tuple[str, dict[str, object], Commitment] | None:
    """Recover one read-only generation from its selected lane-start effect."""
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    if not actor:
        return None
    try:
        _selected_root, attestations = read_attestation_set(root)
    except ValueError:
        return None
    candidates: list[tuple[dict[str, object], Commitment]] = []
    for attestation in attestations:
        if attestation.predicate != "effect:git-ref-update":
            continue
        try:
            plan = plan_from_attestation(attestation)
            effect = git_effect_from_plan(plan)
            validate_git_effect_attestation(
                root,
                effect,
                attestation,
                issuer=attestation.verifier,
                plan=plan,
                current_postconditions=False,
            )
            values = plan.facts.get("values")
            generation = values.get("lease_generation") if isinstance(values, Mapping) else None
            commitment = Commitment.model_validate(plan.commitment, strict=False)
            carrier = f"openspec/changes/{commitment.id.removeprefix('change:')}/commitment.toml"
            update = effect.updates.get(f"refs/heads/{branch}")
            if not isinstance(generation, Mapping):
                continue
            start_head = str(generation.get("expected_head") or "")
            holder = str(generation.get("holder_ref") or "")
            current = exact_commitment_fields(
                root,
                head=head,
                carrier=carrier,
                change_id=commitment.id.removeprefix("change:"),
            )
            observed = load_commitment(
                root,
                carrier=carrier,
                change_id=commitment.id.removeprefix("change:"),
                tree_ref=head,
                expected_digest=commitment.digest(),
            )
        except (TypeError, ValueError):
            continue
        if (
            plan.policy.get("transition") == "lane.start"
            and generation.get("branch") == branch
            and holder == actor == attestation.verifier
            and generation.get("base_commitment_path") == carrier
            and generation.get("base_commitment_digest") == commitment.digest()
            and plan.inputs.commitment == commitment.digest()
            and update is not None
            and update.desired == start_head
            and is_ancestor(root, start_head, head)
            and observed.digest() == commitment.digest()
        ):
            candidates.append(
                (
                    {
                        **generation,
                        **current,
                        "lane_ref": branch,
                        "lease_state": "ownerless_recovery",
                        "commitment_binding": "bound",
                    },
                    observed,
                )
            )
    return (head, *candidates[0]) if len(candidates) == 1 else None


def archive_binding(
    root: Path,
    *,
    head: str,
    change: str,
    lease: dict[str, object],
    target_carrier: str = "",
    environment: Mapping[str, str] | None = None,
) -> tuple[str, str, str] | None:
    """Resolve active, staged, or committed archive carrier authority."""
    carrier = str(lease.get("base_commitment_path") or "")
    if valid_archive_carrier(carrier, change):
        return bound_archive_binding(root, head=head, change=change, carrier=carrier)
    try:
        tree = run_git(root, "write-tree", env=environment).stdout.strip()
        active = f"openspec/changes/{change}/commitment.toml"
        head_tree = current_tree(root, head, environment=environment)
        commitments = active_commitments(root, tree, environment=environment)
        if tree != head_tree and carrier == active and carrier in commitments:
            target = exact_commitment_fields(
                root,
                head=tree,
                carrier=carrier,
                change_id=change,
                environment=dict(environment or {}),
            )
            if not commitment_binding_mismatch(target, lease):
                return "completion_transition", target["expected_tree"], carrier
        inferred = target_carrier or staged_archive_carrier(
            root,
            head=head,
            tree=tree,
            lease=lease,
            change=change,
            environment=environment,
        )
        target = exact_commitment_fields(
            root,
            head=tree,
            carrier=inferred,
            change_id=change,
            environment=dict(environment or {}),
        )
    except ValueError:
        return None
    target_carrier = target["base_commitment_path"]
    if not valid_archive_carrier(target_carrier, change) or commitment_binding_mismatch(
        target, lease
    ):
        return None
    return "archive_transition", target["expected_tree"], target_carrier


def staged_archive_carrier(
    root: Path,
    *,
    head: str,
    tree: str,
    lease: dict[str, object],
    change: str,
    environment: Mapping[str, str] | None = None,
) -> str:
    """Return the sole exact staged archive commitment carrier."""
    active = f"openspec/changes/{change}/commitment.toml"

    def object_id(specification: str) -> str:
        result = run_git(root, "rev-parse", specification, check=False, env=environment)
        return result.stdout.strip() if result.returncode == 0 else ""

    if object_id(f"{tree}:{active}"):
        message = "openspec_active_commitment_not_relocated"
        raise ValueError(message)
    listed = run_git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        tree,
        "--",
        "openspec/changes/archive",
        check=False,
        env=environment,
    )
    if listed.returncode:
        message = "openspec_archive_tree_unreadable"
        raise ValueError(message)
    candidates = [
        carrier
        for carrier in listed.stdout.splitlines()
        if _archive_candidate_matches(
            root,
            carrier=carrier,
            change=change,
            head=head,
            tree=tree,
            expected=lease,
            object_id=object_id,
            environment=environment,
        )
    ]
    if len(candidates) != 1:
        message = "lease_base_commitment_path_mismatch"
        raise ValueError(message)
    return candidates[0]


def _archive_candidate_matches(
    root: Path,
    *,
    carrier: str,
    change: str,
    head: str,
    tree: str,
    expected: Mapping[str, object],
    object_id: Callable[[str], str],
    environment: Mapping[str, str] | None,
) -> bool:
    if not valid_archive_carrier(carrier, change):
        return False
    try:
        target = exact_commitment_fields(
            root,
            head=tree,
            carrier=carrier,
            change_id=change,
            environment=dict(environment or {}),
        )
    except ValueError:
        return False
    if commitment_binding_mismatch(target, expected):
        return False
    if object_id(f"{head}:{carrier}") != object_id(f"{tree}:{carrier}"):
        return True
    archive = carrier.removesuffix("/commitment.toml")
    previous_tree = object_id(f"{head}:{archive}")
    preserved = collision_preservation_path(archive, previous_tree, head)
    return bool(previous_tree and object_id(f"{tree}:{preserved}") == previous_tree)


def bound_archive_binding(
    root: Path, *, head: str, change: str, carrier: str
) -> tuple[str, str, str] | None:
    """Recognize an archive carrier already bound by the current Lease."""
    source = f"openspec/changes/{change}/commitment.toml"
    if not git_stdout(root, "rev-parse", f"{head}:{source}"):
        return "post_archive_closeout", current_tree(root, head), carrier
    for revision in git_stdout(root, "rev-list", head, "--", source, carrier).splitlines():
        parents = run_git(root, "rev-list", "--parents", "-n", "1", revision).stdout.split()
        if len(parents) == 2 and exact_carrier_relocation(
            root, parents[1], revision, source, carrier
        ):
            return "post_archive_closeout", current_tree(root, head), carrier
    return None


def exact_carrier_relocation(
    root: Path, parent: str, revision: str, source: str, carrier: str
) -> bool:
    """Recognize semantic carrier relocation without Git rename heuristics."""
    source_blob = git_stdout(root, "rev-parse", f"{parent}:{source}")
    target_blob = git_stdout(root, "rev-parse", f"{revision}:{carrier}")
    return bool(
        source_blob
        and source_blob == target_blob
        and not git_stdout(root, "rev-parse", f"{revision}:{source}")
    )


def valid_archive_carrier(carrier: str, change: str) -> bool:
    """Return whether a carrier has the exact dated archive identity."""
    match = ARCHIVE_COMMITMENT.fullmatch(carrier)
    if match is None or match[2] != change:
        return False
    try:
        date.fromisoformat(match[1])
    except ValueError:
        return False
    return True


def active_commitments(
    root: Path,
    tree: str,
    *,
    environment: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """List active Commitment carriers in one tree, failing closed."""
    listed = run_git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        tree,
        "--",
        "openspec/changes",
        check=False,
        env=environment,
    )
    if listed.returncode:
        return ("unreadable",)
    return tuple(path for path in listed.stdout.splitlines() if ACTIVE_COMMITMENT.fullmatch(path))


def collision_preservation_path(path: str, tree: str, head: str) -> str:
    """Return the deterministic immutable preservation path for a collision."""
    suffix = hashlib.sha256(f"{tree}\0{head}".encode()).hexdigest()[:12]
    return f"{path}-{suffix}"
