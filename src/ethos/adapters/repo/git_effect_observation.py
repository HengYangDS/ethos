"""Observe exact Git ref effects and compile their transient plans."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_artifacts import proof_artifact_root
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import resolve_revisions
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.admission import RepositoryIdentityTransition
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_utc_time
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import string_mapping

if TYPE_CHECKING:
    from ethos.contracts.plan import GitEffect
    from ethos.contracts.plan import GitRefUpdate
    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject

_MISMATCH = "git_effect_repository_identity_mismatch"
_ZERO_OIDS = {"0" * 40, "0" * 64, ""}


def observe_git_effect(
    root: Path,
    effect: GitEffect,
    *,
    environment: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Capture the exact Git facts before or after one effect."""
    head = current_tracked_head(root)
    selected = resolve_revisions(
        root, (f"{head}^{{tree}}", *effect.updates, *effect.assertions), environment=environment
    )
    return {
        "observed_at": canonical_utc_time(datetime.now(UTC)),
        "head": head,
        "tree": selected[f"{head}^{{tree}}"],
        "refs": {
            name: selected[name] or "0" * len(update.expected)
            for name, update in effect.updates.items()
        },
        "assertions": {name: selected[name] for name in effect.assertions},
    }


def resolve_git_effect_repository(
    root: Path,
    effect: GitEffect,
    before: dict[str, object],
    *,
    environment: Mapping[str, str] | None = None,
    allow_absent_prestate: bool = False,
    plan: TransitionPlan | None = None,
    current_scope: bool = True,
) -> str:
    """Resolve one repository identity across every revision touched by an effect."""
    revisions = {
        str(before["head"]),
        *(update.expected for update in effect.updates.values()),
        *(update.desired for update in effect.updates.values()),
        *effect.assertions.values(),
    } - _ZERO_OIDS
    expected = {update.expected for update in effect.updates.values()}
    if allow_absent_prestate and all(
        update.desired in _ZERO_OIDS for update in effect.updates.values()
    ):
        retained = {
            revision
            for revision in effect.assertions.values()
            if revision != str(before["head"])
            and any(
                run_git(
                    root, "merge-base", "--is-ancestor", old, revision, check=False, env=environment
                ).returncode
                == 0
                for old in expected
            )
        }
        expected |= retained
    identities: dict[str, str] = {}
    for revision in revisions:
        try:
            identities[revision] = repository_identity(
                root, tree_ref=revision, environment=environment
            )
        except ValueError:
            if allow_absent_prestate and revision in expected:
                continue
            raise
    if plan is not None and "repository_identity_transitions" in plan.policy:
        return _transition_identity(
            root, effect, plan, identities, current_scope=current_scope, environment=environment
        )
    if len(set(identities.values())) != 1:
        raise ValueError(_MISMATCH)
    return next(iter(identities.values()))


def compile_observed_git_effect(
    root: Path,
    commitment: Commitment | None,
    effect: GitEffect,
    *,
    head: str,
    policy: JsonObject,
    prior_attestations: JsonObject | None = None,
    values: Mapping[str, object] | None = None,
    environment: Mapping[str, str] | None = None,
    identity_transition: bool = False,
) -> TransitionPlan:
    """Compile one Git effect directly from fresh repository observations."""
    extra = dict(values or {})
    semantic_operation = str(policy.get("transition") or policy["operation"])
    effect_policy = {
        **policy,
        "operation": "git.ref.compare-and-swap",
        "transition": semantic_operation,
        "effect_digest": effect.digest(),
    }
    if identity_transition:
        _require_identity_operation(semantic_operation)
        relations, coordination = _observe_identity_transition(
            root, effect, prior_attestations or {}, environment=environment
        )
        extra["lease_generation"] = coordination
        effect_policy.update(
            repository_identity_transitions=relations,
            actor=os.environ.get("ETHOS_ACTOR", "").strip(),
            execution_branch=current_branch(root),
        )
    return compile_git_effect_plan(
        commitment,
        Facts(
            repository=repository_identity(root, tree_ref=head, environment=environment),
            head=head,
            tree=current_tree(root, head, environment=environment),
            observed_at=datetime.now(UTC),
            values={
                **extra,
                "refs": {ref: update.expected for ref, update in effect.updates.items()},
                "assertions": effect.assertions,
            },
            source_refs=(
                "git:HEAD",
                "git:HEAD^{tree}",
                *(f"git:{ref}" for ref in sorted((*effect.updates, *effect.assertions))),
                *(("lease:current-generation",) if "lease_generation" in extra else ()),
            ),
        ),
        prior_attestations=prior_attestations or {},
        policy=effect_policy,
        effect=effect,
    )


def _observe_identity_transition(
    root: Path,
    effect: GitEffect,
    prior_attestations: JsonObject,
    *,
    environment: Mapping[str, str] | None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Compile exact identity edges without inventing a second effect or authority store."""
    proof = Attestation.model_validate(mutable_json(prior_attestations.get("proof")))
    proof_plan = plan_from_statement(proof)
    generation = string_mapping(
        string_mapping(proof_plan.facts.get("values")).get("lease_generation")
    )
    branch = str(generation.get("lane_ref") or "")
    lease = leases_by_branch(root).get(branch, {})
    if lease.get("lease_state") != "valid" or not os.environ.get("ETHOS_ACTOR", "").strip():
        message = "repository_identity_transition_live_authority_required"
        raise ValueError(message)
    common, stat = _identity_database(root, environment)
    revisions = {
        revision
        for update in effect.updates.values()
        for revision in (update.expected, update.desired)
    } - _ZERO_OIDS
    identities = {
        revision: repository_identity(root, tree_ref=revision, environment=environment)
        for revision in revisions
    }
    relations = [
        RepositoryIdentityTransition(
            target_ref=ref,
            expected_head=update.expected,
            expected_tree=current_tree(root, update.expected, environment=environment),
            desired_head=update.desired,
            desired_tree=current_tree(root, update.desired, environment=environment),
            old_identity=identities[update.expected],
            new_identity=identities[update.desired],
            common_directory=common.as_posix(),
            common_device=stat.st_dev,
            common_inode=stat.st_ino,
        ).model_dump(mode="json")
        for ref, update in _identity_transition_updates(effect, identities).items()
    ]
    return relations, lease_generation(lease)


def _require_identity_operation(operation: str) -> None:
    """Identity migration refines integration, never arbitrary ref mutation authority."""
    if operation not in {"candidate.integrate", "candidate.accept", "release.promote"}:
        message = "repository_identity_transition_operation_unsupported"
        raise ValueError(message)


def _identity_transition_updates(
    effect: GitEffect, identities: Mapping[str, str]
) -> dict[str, GitRefUpdate]:
    """Separate actual branch identity edges from same-identity and newly created refs."""
    updates = {
        ref: update
        for ref, update in effect.updates.items()
        if update.expected in identities
        and update.desired in identities
        and identities[update.expected] != identities[update.desired]
    }
    if not updates or any(not ref.startswith("refs/heads/") for ref in updates):
        message = "repository_identity_transition_scope_mismatch"
        raise ValueError(message)
    return updates


def _transition_identity(
    root: Path,
    effect: GitEffect,
    plan: TransitionPlan,
    identities: dict[str, str],
    *,
    current_scope: bool,
    environment: Mapping[str, str] | None,
) -> str:
    """Validate one typed relation set at both effect admission and result verification."""
    _require_identity_operation(str(plan.policy.get("transition") or ""))
    raw = plan.policy["repository_identity_transitions"]
    if not isinstance(raw, list | tuple) or not raw:
        message = "repository_identity_transition_invalid"
        raise ValueError(message)
    transitions = tuple(
        RepositoryIdentityTransition.model_validate(mutable_json(item)) for item in raw
    )
    changed = _identity_transition_updates(effect, identities)
    if len(transitions) != len(changed) or {item.target_ref for item in transitions} != set(
        changed
    ):
        message = "repository_identity_transition_scope_mismatch"
        raise ValueError(message)
    common, stat = _identity_database(root, environment)
    old: dict[str, str] = {}
    for item in transitions:
        update = effect.updates[item.target_ref]
        if (
            (item.expected_head, item.desired_head) != (update.expected, update.desired)
            or item.expected_tree != current_tree(root, update.expected, environment=environment)
            or item.desired_tree != current_tree(root, update.desired, environment=environment)
            or item.old_identity != identities.get(update.expected)
            or item.new_identity != identities.get(update.desired)
            or run_git(
                root,
                "merge-base",
                "--is-ancestor",
                update.expected,
                update.desired,
                check=False,
                env=environment,
            ).returncode
            or (
                current_scope
                and (item.common_directory, item.common_device, item.common_inode)
                != (common.as_posix(), stat.st_dev, stat.st_ino)
            )
        ):
            message = "repository_identity_transition_binding_mismatch"
            raise ValueError(message)
        old[item.expected_head] = item.old_identity
    destinations = {item.new_identity for item in transitions}
    if len(destinations) != 1 or any(
        identity not in destinations and old.get(revision) != identity
        for revision, identity in identities.items()
    ):
        raise ValueError(_MISMATCH)
    _require_transition_proof(root, plan, transitions)
    return destinations.pop()


def _identity_database(
    root: Path, environment: Mapping[str, str] | None
) -> tuple[Path, os.stat_result]:
    """Fence the actual Git process to the request's common object database."""
    common = Path(git_common_dir(root)).resolve()
    if environment is not None:
        actual = Path(
            run_git(
                root, "rev-parse", "--path-format=absolute", "--git-common-dir", env=environment
            ).stdout.strip()
        ).resolve()
        if actual != common:
            message = "repository_identity_transition_database_mismatch"
            raise ValueError(message)
    return common, common.stat()


def _require_transition_proof(
    root: Path, plan: TransitionPlan, transitions: tuple[RepositoryIdentityTransition, ...]
) -> None:
    """Validate carried immutable evidence without treating it as current authorization."""
    proof = Attestation.model_validate(mutable_json(plan.prior_attestations.get("proof")))
    proof_plan = plan_from_statement(proof)
    head = str(proof_plan.facts.get("head") or "")
    generation = string_mapping(plan.facts.get("values")).get("lease_generation")
    checks, gaps = artifact_checks(proof_artifact_root(root), proof)
    if (
        not proof.commitment_digest
        or not isinstance(generation, Mapping)
        or not plan.authority.get("actor")
        or plan.authority["actor"] != generation.get("holder_ref")
        or any(item.desired_head != head for item in transitions)
        or any(item.new_identity != proof_plan.facts.get("repository") for item in transitions)
        or any(item.desired_tree != proof_plan.facts.get("tree") for item in transitions)
        or (
            plan.inputs.commitment is not None and plan.inputs.commitment != proof.commitment_digest
        )
        or checks is None
        or gaps
        or proof_statement_gaps(proof, checks)
    ):
        message = "repository_identity_transition_authority_mismatch"
        raise ValueError(message)
