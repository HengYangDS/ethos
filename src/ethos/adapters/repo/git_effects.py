"""Execute and attest exact Git ref effects."""

from __future__ import annotations

import os
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
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import observe_git_effect
from ethos.adapters.repo.git_effect_observation import resolve_git_effect_repository
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation


def execute_git_effect(
    root: Path,
    plan: TransitionPlan,
    *,
    issuer: str,
    environment: Mapping[str, str] | None = None,
) -> Attestation:
    """Recognize, execute, or recover one exact Git ref transaction."""
    effect = git_effect_from_plan(plan)
    _require_effect_permission(effect, plan.permissions)
    recorded = ethos.adapters.repo.git_effect_attestation.records(root, plan)
    if attestation := next(iter(recorded), None):
        ethos.adapters.repo.git_effect_attestation.validate(
            root, effect, attestation, issuer=issuer, plan=plan
        )
        _clear_effect_intents(root, plan, effect)
        return attestation
    observed = observe_git_effect(root, effect, environment=environment)
    refs = cast("dict[str, str]", observed["refs"])
    expected = {name: update.expected for name, update in effect.updates.items()}
    desired = {name: update.desired for name, update in effect.updates.items()}
    recovering = refs == desired
    if observed["assertions"] != effect.assertions:
        raise ValueError("git_effect_cas_mismatch")
    if recovering:
        _require_live_lease(root, plan, environment=environment)
    intents: list[dict[str, object]] = []
    applied = False
    try:
        if recovering:
            intents = _claim_effect_intents(root, plan, effect, phase="recover")
        else:
            _require_plan_prestate(root, plan, effect, environment=environment)
            repository = resolve_git_effect_repository(
                root, effect, observed, environment=environment
            )
            if refs != expected:
                raise ValueError("git_effect_cas_mismatch")
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
                raise ValueError("git_effect_cas_rejected")
            applied = True
            _claim_effect_intents(root, plan, effect, phase="committed")
        after = observe_git_effect(root, effect, environment=environment)
        if cast("dict[str, str]", after["refs"]) != desired:
            raise ValueError("git_effect_postcondition_failed")
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
        for claimed in intents:
            clear_ref_intent(root, str(claimed["nonce"]))
        return attestation
    finally:
        if not applied and not recovering:
            _abort_effect_intents(root, effect, intents)


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
                        recoverable=True,
                    )
                )
            current = claim_ref_intent(
                root=root,
                ref_name=ref_name,
                update=update,
                operation=operation,
                phase=phase,
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


def _clear_effect_intents(root: Path, plan: TransitionPlan, effect: GitEffect) -> None:
    for intent in _claim_effect_intents(
        root,
        plan,
        effect,
        phase="recover",
        missing_ok=True,
    ):
        clear_ref_intent(root, str(intent["nonce"]))


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
        if operation == "candidate.accept" and ref_name == release_ref
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
    hooks = candidate / ".githooks"
    hook = hooks / "reference-transaction"
    if hooks.is_symlink() or not hooks.is_dir():
        message = "git_effect_candidate_hook_invalid"
        raise ValueError(message)
    if hook.is_symlink() or not hook.is_file() or not os.access(hook, os.X_OK):
        message = "git_effect_candidate_hook_invalid"
        raise ValueError(message)
    return {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": hooks.as_posix(),
    }


def _require_effect_permission(effect: GitEffect, permissions: tuple[str, ...]) -> None:
    admitted = set(permissions)
    if "git.ref.compare-and-swap" not in admitted and not set(effect.permissions) <= admitted:
        message = "git_effect_permission_denied"
        raise ValueError(message)


def _require_plan_prestate(
    root: Path,
    plan: TransitionPlan,
    effect: GitEffect,
    *,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Reject a carried plan whose exact mutation facts have gone stale."""
    values = plan.facts.get("values")
    facts = values if isinstance(values, Mapping) else {}
    expected_refs = {ref: update.expected for ref, update in effect.updates.items()}
    if facts.get("refs") != expected_refs or facts.get("assertions") != effect.assertions:
        message = "git_effect_plan_prestate_mismatch"
        raise ValueError(message)
    _require_live_lease(root, plan, environment=environment)
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
        if (
            current.get("lease_state") != "valid"
            or current.get("commitment_binding") != "bound"
            or mutable_json(generation) != mutable_json(lease_generation(current))
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
        elif operation != "lane.start.compensate" and run_git(
            root, "branch", "--show-current"
        ).stdout.strip() != str(plan.policy.get("execution_branch") or branch):
            message = "git_effect_lease_branch_mismatch"
            raise ValueError(message)
