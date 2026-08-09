"""Execute and attest exact Git ref effects."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

import ethos.adapters.repo.git_effect_attestation
from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.admission.ref_intent import clear_ref_intent
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import effective_git_config_value
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import observe_git_effect
from ethos.adapters.repo.git_effect_observation import resolve_git_effect_repository
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from typing import Any

    from ethos.contracts.semantic import Attestation


def stage_git_paths(
    root: Path,
    paths: tuple[str, ...],
    *,
    runner: Callable[..., Any] = run_git,
) -> None:
    """Stage one exact non-empty path set through the sole Git effect owner."""
    if not paths:
        message = "git_effect_stage_paths_missing"
        raise ValueError(message)
    completed = runner(root, "add", *paths, check=False)
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "git_effect_stage_failed")


def stage_git_worktree(root: Path, *, previous: str) -> None:
    """Stage the complete current delta at one exact pre-effect HEAD."""
    if current_tracked_head(root) != previous:
        message = "git_effect_head_stale"
        raise ValueError(message)
    completed = run_git(root, "add", "--all", check=False)
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "git_effect_stage_failed")


def move_tracked_tree(root: Path, source: str, target: str) -> None:
    """Move one tracked directory without overwriting another filesystem entry."""
    source_path = (root / source).resolve()
    target_path = (root / target).resolve()
    try:
        source_path.relative_to(root.resolve())
        target_path.relative_to(root.resolve())
    except ValueError as error:
        message = "git_effect_move_path_outside_root"
        raise ValueError(message) from error
    if (
        not source_path.is_dir()
        or source_path.is_symlink()
        or os.path.lexists(target_path)
        or target_path.parent.is_symlink()
    ):
        message = "git_effect_move_binding_stale"
        raise ValueError(message)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.rename(target_path)


def commit_git_worktree(
    root: Path,
    *,
    previous: str,
    message: str,
    environment: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Commit the staged Git effect through normal hooks at one exact HEAD."""
    if current_tracked_head(root) != previous:
        message = "git_effect_head_stale"
        raise ValueError(message)
    completed = run_git(
        root,
        "commit",
        "-m",
        message,
        check=False,
        env=_commit_environment(root, environment),
    )
    return {
        "verdict": "pass" if completed.returncode == 0 else "block",
        "error": completed.stderr.strip(),
    }


def _commit_environment(root: Path, environment: Mapping[str, str] | None) -> dict[str, str] | None:
    bound = dict(environment or {})
    signing = run_git(root, "config", "--local", "--get", "user.signingkey", check=False)
    if signing.returncode:
        return bound or None
    key = Path(signing.stdout.strip())
    if not key.is_absolute() or not key.is_file():
        message = "git_effect_signing_key_invalid"
        raise ValueError(message)
    public_key = key.read_text(encoding="utf-8").strip()
    if not public_key.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-sha2-")):
        message = "git_effect_signing_key_invalid"
        raise ValueError(message)
    signer_value = effective_git_config_value(root, "gpg.ssh.program")
    signing_value = f"key::{public_key}"
    signing_inputs: tuple[tuple[str, str], ...] = ()
    if signer_value:
        signer = Path(signer_value)
        if not signer.is_absolute() or not signer.is_file() or not os.access(signer, os.X_OK):
            message = "git_effect_signing_program_invalid"
            raise ValueError(message)
        signing_value = key.as_posix()
        signing_inputs = (("gpg.ssh.program", signer.as_posix()),)
    count = int(bound.get("GIT_CONFIG_COUNT", "0"))
    for name, value in (
        ("gpg.format", "ssh"),
        *signing_inputs,
        ("user.signingkey", signing_value),
    ):
        bound[f"GIT_CONFIG_KEY_{count}"] = name
        bound[f"GIT_CONFIG_VALUE_{count}"] = value
        count += 1
    bound["GIT_CONFIG_COUNT"] = str(count)
    return bound


def compensate_git_worktree(root: Path, *, head: str, untracked_path: str = "") -> None:
    """Compensate one failed workspace effect back to its exact pre-effect tree."""
    completed = run_git(
        root,
        "restore",
        "--source",
        head,
        "--staged",
        "--worktree",
        ".",
        check=False,
    )
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "git_effect_compensation_failed")
    if untracked_path:
        _remove_tree(root, untracked_path)


def compensate_created_paths(
    root: Path,
    *,
    head: str,
    paths: tuple[str, ...],
    untracked_root: str,
) -> None:
    """Remove only newly created staged paths while preserving a prior overlay."""
    completed = run_git(
        root,
        "restore",
        "--source",
        head,
        "--staged",
        "--",
        *paths,
        check=False,
    )
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "git_effect_compensation_failed")
    _remove_tree(root, untracked_root)


def remove_untracked_tree(root: Path, path: str) -> None:
    """Remove one newly created untracked directory through the Git effect owner."""
    _remove_tree(root, path)


def _remove_tree(root: Path, path: str) -> None:
    """Apply the sole containment and type check for effect-owned tree removal."""
    target = (root / path).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        msg = "git_effect_compensation_path_outside_root"
        raise ValueError(msg) from error
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        msg = "git_effect_compensation_path_unsafe"
        raise ValueError(msg)
    if target.exists():
        shutil.rmtree(target, ignore_errors=False)


def execute_git_effect(
    root: Path,
    plan: TransitionPlan,
    *,
    issuer: str,
    environment: Mapping[str, str] | None = None,
    projection: Callable[[], None] | None = None,
    detached_branch: str = "",
) -> Attestation:
    """Recognize, execute, or recover one exact Git ref transaction."""
    effect = git_effect_from_plan(plan)
    _require_effect_permission(effect, plan)
    recorded = ethos.adapters.repo.git_effect_attestation.records(root, plan)
    if attestation := next(iter(recorded), None):
        ethos.adapters.repo.git_effect_attestation.validate(
            root, effect, attestation, issuer=issuer, plan=plan
        )
        _require_live_lease(
            root,
            plan,
            environment=environment,
            detached_branch=detached_branch,
            recovering=True,
        )
        intents = _claim_effect_intents(
            root, plan, effect, phase="recover", missing_ok=projection is None
        )
        _project_and_clear(root, intents, projection)
        return attestation
    observed, recovering, repository = _admit_git_effect(
        root,
        plan,
        effect,
        environment=environment,
        detached_branch=detached_branch,
    )
    desired = {name: update.desired for name, update in effect.updates.items()}
    intents: list[dict[str, object]] = []
    applied = False
    try:
        if recovering:
            intents = _claim_effect_intents(root, plan, effect, phase="recover")
        else:
            intents = _claim_effect_intents(root, plan, effect, phase="prepared")
            completed = run_git(
                root,
                "update-ref",
                "--stdin",
                "-z",
                check=False,
                env={**(_effect_environment(root, plan, effect) or {}), **(environment or {})},
                stdin=effect.program(),
                text=False,
            )
            if completed.returncode:
                msg = "git_effect_cas_rejected"
                raise ValueError(msg)
            applied = True
            _claim_effect_intents(root, plan, effect, phase="committed")
        after = observe_git_effect(root, effect, environment=environment)
        if cast("dict[str, str]", after["refs"]) != desired:
            msg = "git_effect_postcondition_failed"
            raise ValueError(msg)
        attestation = ethos.adapters.repo.git_effect_attestation.issue(
            effect,
            plan=plan,
            issuer=issuer,
            evidence=(
                repository if not recovering else str(plan.facts.get("repository") or ""),
                "recovered" if recovering else "applied",
                observed,
                after,
            ),
        )
        ethos.adapters.repo.git_effect_attestation.records(root, plan, attestation)
        _project_and_clear(root, intents, projection)
        return attestation
    finally:
        if not applied and not recovering:
            _abort_effect_intents(root, effect, intents)


def admit_git_effect(
    root: Path,
    plan: TransitionPlan,
    *,
    environment: Mapping[str, str] | None = None,
    detached_branch: str = "",
) -> None:
    """Validate the exact Git effect plan without claiming intents or mutating refs."""
    effect = git_effect_from_plan(plan)
    _require_effect_permission(effect, plan)
    _admit_git_effect(
        root,
        plan,
        effect,
        environment=environment,
        detached_branch=detached_branch,
    )


def _admit_git_effect(
    root: Path,
    plan: TransitionPlan,
    effect: GitEffect,
    *,
    environment: Mapping[str, str] | None,
    detached_branch: str,
) -> tuple[dict[str, object], bool, str]:
    """Return one fully admitted current observation shared by dry-run and apply."""
    observed = observe_git_effect(root, effect, environment=environment)
    refs = cast("dict[str, str]", observed["refs"])
    expected = {name: update.expected for name, update in effect.updates.items()}
    desired = {name: update.desired for name, update in effect.updates.items()}
    recovering = refs == desired
    if observed["assertions"] != effect.assertions:
        message = "git_effect_cas_mismatch"
        raise ValueError(message)
    if recovering:
        _require_live_lease(
            root,
            plan,
            environment=environment,
            detached_branch=detached_branch,
            recovering=True,
        )
        return observed, True, ""
    _require_plan_prestate(
        root,
        plan,
        effect,
        environment=environment,
        detached_branch=detached_branch,
    )
    repository = resolve_git_effect_repository(
        root,
        effect,
        observed,
        environment=environment,
        allow_missing_prestate=(plan.policy.get("repository_commitment_bootstrap") is True),
    )
    if refs != expected:
        message = "git_effect_cas_mismatch"
        raise ValueError(message)
    return observed, False, repository


def _claim_effect_intents(
    root: Path,
    plan: TransitionPlan,
    effect: GitEffect,
    *,
    phase: Literal["prepared", "committed", "recover"],
    missing_ok: bool = False,
) -> list[dict[str, object]]:
    claimed: list[dict[str, object]] = []
    try:
        for ref_name, update in effect.updates.items():
            operation = _ref_operation(plan, ref_name)
            if phase == "prepared":
                claimed.append(
                    write_ref_intent(
                        root=root,
                        ref_name=ref_name,
                        update=update,
                        operation=operation,
                        plan_digest=plan.digest,
                    )
                )
            current = claim_ref_intent(
                root=root,
                ref_name=ref_name,
                update=update,
                operation=operation,
                phase=phase,
                plan_digest=plan.digest,
            )
            if missing_ok and current["gap"] == "ref_intent_missing":
                continue
            _raise_intent_gap(current, phase)
            if phase == "prepared":
                claimed[-1] = current
            else:
                claimed.append(current)
    except (OSError, ValueError):
        if phase == "prepared":
            _abort_effect_intents(root, effect, claimed)
        raise
    return claimed


def _clear_claimed_intents(root: Path, intents: list[dict[str, object]]) -> None:
    for intent in intents:
        clear_ref_intent(root, str(intent["nonce"]))


def _project_and_clear(
    root: Path, intents: list[dict[str, object]], projection: Callable[[], None] | None
) -> None:
    if projection:
        projection()
    _clear_claimed_intents(root, intents)


def _raise_intent_gap(
    claimed: Mapping[str, object], phase: Literal["prepared", "committed", "recover"]
) -> None:
    gap = str(claimed["gap"] or "")
    if not gap:
        return
    prefix = "git_effect_recovery" if phase == "recover" else f"git_effect_ref_intent_{phase}"
    suffix = "intent_missing" if phase == "recover" and gap == "ref_intent_missing" else gap
    message = f"{prefix}_{suffix}"
    raise ValueError(message)


def _abort_effect_intents(root: Path, effect: GitEffect, intents: list[dict[str, object]]) -> None:
    for intent in intents:
        ref_name = str(intent["ref_name"])
        claim_ref_intent(
            root=root,
            ref_name=ref_name,
            update=effect.updates[ref_name],
            operation=str(intent["operation"]),
            phase="aborted",
        )


def _ref_operation(plan: TransitionPlan, ref_name: str) -> str:
    operation = str(plan.policy.get("operation") or "")
    release_ref = f"refs/heads/{plan.policy.get('release_branch') or ''}"
    return (
        "release.mirror"
        if operation in {"candidate.accept", "commit.identity-replace"} and ref_name == release_ref
        else operation
    )


def _effect_environment(
    root: Path, plan: TransitionPlan, effect: GitEffect
) -> dict[str, str] | None:
    operation = str(plan.policy.get("operation") or "")
    if operation.startswith("lane.start"):
        return {"ETHOS_ACTOR": str(plan.policy.get("holder_ref") or "")}
    if operation != "candidate.accept":
        return None
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    candidate = Path(str(facts.get("candidate_worktree_path") or ""))
    candidate_branch = str(plan.policy.get("candidate_branch") or "")
    expected = {update.desired for update in effect.updates.values()}
    if (
        len(expected) != 1
        or not candidate.is_absolute()
        or not candidate.is_dir()
        or git_common_dir(candidate) != git_common_dir(root)
        or run_git(candidate, "branch", "--show-current").stdout.strip() != candidate_branch
        or current_tracked_head(candidate) != expected.pop()
        or bool(run_git(candidate, "status", "--short").stdout.strip())
    ):
        message = "git_effect_candidate_binding_stale"
        raise ValueError(message)
    runtime = hook_runtime_binding(candidate)
    if runtime["required_gaps"]:
        message = "git_effect_candidate_hook_invalid:" + ",".join(runtime["required_gaps"])
        raise ValueError(message)
    return {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": str(runtime["hooks_path"]),
    }


def _require_effect_permission(effect: GitEffect, plan: TransitionPlan) -> None:
    """Admit one CAS through its Commitment or its narrow lease-bound bootstrap."""
    admitted = set(plan.permissions)
    if "git.ref.compare-and-swap" in admitted or set(effect.permissions) <= admitted:
        return
    if _is_commitment_rebind_authority(effect, plan) or _is_candidate_integration_authority(
        effect, plan
    ):
        return
    msg = "git_effect_permission_denied"
    raise ValueError(msg)


def _is_commitment_rebind_authority(effect: GitEffect, plan: TransitionPlan) -> bool:
    """Recognize rebind's command-level CAS authority without widening normal effects."""
    if plan.policy.get("operation") not in {"commitment.rebind", "change.identity-repair"}:
        return False
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    generation = facts.get("lease_generation")
    successor = facts.get("lease_successor")
    if not isinstance(generation, Mapping) or not isinstance(successor, Mapping):
        return False
    updates = tuple(effect.updates.items())
    if len(updates) != 1:
        return False
    ref, update = updates[0]
    expected_branch = f"refs/heads/{generation.get('branch') or ''}"
    new_digest = str(facts.get("new_commitment_digest") or "")
    return (
        ref == expected_branch
        and update.expected == generation.get("expected_head")
        and update.desired == successor.get("expected_head")
        and successor.get("epoch") == int(generation.get("epoch") or 0) + 1
        and successor.get("holder_ref") == generation.get("holder_ref")
        and successor.get("lease_id") == generation.get("lease_id")
        and successor.get("lane_incarnation_id") == generation.get("lane_incarnation_id")
        and facts.get("new_commitment_path") == successor.get("base_commitment_path")
        and facts.get("new_commitment_bytes_sha256")
        == successor.get("base_commitment_bytes_sha256")
        and new_digest == successor.get("base_commitment_digest")
        and plan.policy.get("old_commitment_digest") == generation.get("base_commitment_digest")
        and plan.policy.get("new_commitment_digest") == new_digest
    )


def _is_candidate_integration_authority(effect: GitEffect, plan: TransitionPlan) -> bool:
    """Recognize one exact proof- and Lease-bound candidate integration CAS."""
    if plan.policy.get("operation") != "candidate.integrate":
        return False
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    generation = facts.get("lease_generation")
    proof = plan.prior_attestations.get("proof")
    if not isinstance(generation, Mapping) or not isinstance(proof, Mapping):
        return False
    updates, assertions = tuple(effect.updates.items()), tuple(effect.assertions.items())
    if len(updates) != 1 or len(assertions) != 1:
        return False
    ref, update = updates[0]
    source_ref, source_head = assertions[0]
    candidate = str(plan.policy.get("candidate_branch") or "")
    proof_statement = proof.get("statement")
    statement = proof_statement if isinstance(proof_statement, Mapping) else {}
    return (
        bool(candidate)
        and ref == f"refs/heads/{candidate}"
        and source_ref == f"refs/heads/{generation.get('branch') or ''}"
        and source_head == update.desired == plan.facts.get("head")
        and update.expected != update.desired
        and generation.get("expected_head") == update.desired
        and proof.get("predicate") == "proof:execution"
        and proof.get("verdict") == "pass"
        and proof.get("subject") == f"git:commit:{update.desired}"
        and statement.get("head", update.desired) == update.desired
        and proof.get("commitment_digest") == generation.get("base_commitment_digest")
        and proof.get("commitment_digest") == plan.inputs.commitment
    )


def _require_plan_prestate(
    root: Path,
    plan: TransitionPlan,
    effect: GitEffect,
    *,
    environment: Mapping[str, str] | None = None,
    detached_branch: str = "",
) -> None:
    """Reject a carried plan whose exact mutation facts have gone stale."""
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    expected_refs = {ref: update.expected for ref, update in effect.updates.items()}
    if facts.get("refs") != expected_refs or facts.get("assertions") != effect.assertions:
        message = "git_effect_plan_prestate_mismatch"
        raise ValueError(message)
    _require_live_lease(
        root,
        plan,
        environment=environment,
        detached_branch=detached_branch,
    )
    head = str(plan.facts.get("head") or "")
    tree = str(plan.facts.get("tree") or "")
    current = current_tracked_head(root)
    operation = str(plan.policy.get("operation") or "")
    if operation == "lane.start.compensate":
        if head not in {update.expected for update in effect.updates.values()}:
            message = "git_effect_plan_prestate_stale"
            raise ValueError(message)
    elif current != head:
        message = "git_effect_plan_prestate_stale"
        raise ValueError(message)
    if current_tree(root, head) != tree:
        message = "git_effect_plan_prestate_stale"
        raise ValueError(message)


def _require_live_lease(
    root: Path,
    plan: TransitionPlan,
    *,
    environment: Mapping[str, str] | None = None,
    detached_branch: str = "",
    recovering: bool = False,
) -> None:
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    generation = facts.get("lease_generation")
    if isinstance(generation, Mapping):
        branch = str(generation.get("branch") or "")
        current = leases_by_branch(
            root,
            object_environment=dict(environment or {}),
        ).get(branch, {})
        live = lease_generation(current)
        stable = ("branch", "lane_incarnation_id", "lease_id", "holder_ref")
        recovery_match = recovering and all(generation.get(key) == live.get(key) for key in stable)
        successor = facts.get("lease_successor")
        if isinstance(successor, Mapping):
            recovery_match = (
                recovery_match
                and set(successor) == set(live) - {"payload_sha256"}
                and all(
                    mutable_json(live.get(key)) == mutable_json(value)
                    for key, value in successor.items()
                )
            )
        else:
            recovery_match = recovery_match and (
                generation.get("epoch") == live.get("epoch")
                and live.get("expected_head")
                in {generation.get("expected_head"), plan.facts.get("head")}
            )
        if (
            current.get("lease_state") != "valid"
            or current.get("commitment_binding") != "bound"
            or not (mutable_json(generation) == mutable_json(live) or recovery_match)
        ):
            message = "git_effect_lease_generation_stale"
            raise ValueError(message)
        operation = str(plan.policy.get("operation") or "")
        actor = (
            str(plan.policy.get("holder_ref") or "")
            if operation.startswith("lane.start")
            else os.environ.get("ETHOS_ACTOR", "").strip()
        )
        if actor != str(generation.get("holder_ref") or ""):
            message = "lease_actor_mismatch"
            raise ValueError(message)
        if operation == "lane.start":
            if run_git(root, "branch", "--show-current").stdout.strip():
                message = "git_effect_lease_branch_mismatch"
                raise ValueError(message)
        elif operation != "lane.start.compensate":
            execution_branch = str(plan.policy.get("execution_branch") or branch)
            attached_branch = run_git(root, "branch", "--show-current").stdout.strip()
            if attached_branch != execution_branch and not (
                detached_branch == execution_branch
                and not attached_branch
                and current_tracked_head(root) == str(plan.facts.get("head") or "")
            ):
                message = "git_effect_lease_branch_mismatch"
                raise ValueError(message)
