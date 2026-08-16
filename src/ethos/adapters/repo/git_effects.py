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
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_admission import require_effect_permission
from ethos.adapters.repo.git_effect_admission import require_live_lease
from ethos.adapters.repo.git_effect_admission import require_plan_prestate
from ethos.adapters.repo.git_effect_observation import observe_git_effect
from ethos.adapters.repo.git_effect_observation import resolve_git_effect_repository
from ethos.adapters.repo.git_signing import commit_environment
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan

_COMMIT_TRANSITION_ENVIRONMENT = frozenset({"ETHOS_ARCHIVE_TRANSITION"})

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
    if hook_gaps := hook_runtime_binding(root)["required_gaps"]:
        raise ValueError(str(hook_gaps[0]))
    environment_keys = frozenset(environment or ())
    if not environment_keys <= _COMMIT_TRANSITION_ENVIRONMENT:
        message = "git_effect_commit_environment_forbidden"
        raise ValueError(message)
    completed = run_git(
        root,
        "commit",
        "-m",
        message,
        check=False,
        env=commit_environment(root, environment),
    )
    return {
        "verdict": "pass" if completed.returncode == 0 else "block",
        "error": completed.stderr.strip(),
    }


def create_git_commit(
    root: Path,
    *,
    tree: str,
    parent: str,
    message: str,
    sign: bool = False,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> Any:
    """Create one commit object through the sole Git mutation owner."""
    commit_environment_binding = commit_environment(root, environment) if sign else environment
    return runner(
        root,
        "commit-tree",
        *(("-S",) if sign else ()),
        tree,
        "-p",
        parent,
        "-m",
        message,
        check=False,
        env=commit_environment_binding,
    )


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
    if not (issuer := issuer.strip()):
        message = "git_effect_issuer_invalid"
        raise ValueError(message)
    effect = git_effect_from_plan(plan)
    require_effect_permission(effect, plan)
    recorded = ethos.adapters.repo.git_effect_attestation.records(
        root, plan, environment=environment
    )
    if attestation := next(iter(recorded), None):
        ethos.adapters.repo.git_effect_attestation.validate(
            root, effect, attestation, issuer=issuer, plan=plan, environment=environment
        )
        require_live_lease(
            root,
            plan,
            environment=environment,
            detached_branch=detached_branch,
            recovering=True,
        )
        intents = _claim_effect_intents(
            root, plan, effect, phase="recover", missing_ok=projection is None
        )
        if projection:
            projection()
        _clear_claimed_intents(root, intents)
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
    persisted = False
    try:
        if recovering:
            intents = _claim_effect_intents(root, plan, effect, phase="recover")
        else:
            intents = _claim_effect_intents(root, plan, effect, phase="prepared")
            _apply_git_ref_transaction(root, plan, effect, environment=environment)
            applied = True
            _claim_effect_intents(root, plan, effect, phase="committed")
        after = _require_effect_postcondition(root, effect, desired, environment=environment)
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
        if projection:
            projection()
        ethos.adapters.repo.git_effect_attestation.records(
            root, plan, attestation, environment=environment
        )
        persisted = True
        _clear_claimed_intents(root, intents)
    except (OSError, TypeError, ValueError) as error:
        if applied and not recovering and not persisted:
            _compensate_git_effect(
                root,
                plan,
                effect,
                intents,
                environment=environment,
                cause=error,
            )
        raise
    else:
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
    require_effect_permission(effect, plan)
    _admit_git_effect(root, plan, effect, environment=environment, detached_branch=detached_branch)


def _run_effect_program(
    root: Path,
    plan: TransitionPlan,
    effect: GitEffect,
    *,
    environment: Mapping[str, str] | None,
) -> Any:
    return run_git(
        root,
        "update-ref",
        "--stdin",
        "-z",
        check=False,
        env={**(_effect_environment(root, plan, effect) or {}), **(environment or {})},
        stdin=effect.program(),
        text=False,
    )


def _apply_git_ref_transaction(
    root: Path,
    plan: TransitionPlan,
    effect: GitEffect,
    *,
    environment: Mapping[str, str] | None,
) -> None:
    if _run_effect_program(root, plan, effect, environment=environment).returncode:
        message = "git_effect_cas_rejected"
        raise ValueError(message)


def _require_effect_postcondition(
    root: Path,
    effect: GitEffect,
    desired: Mapping[str, str],
    *,
    environment: Mapping[str, str] | None,
) -> dict[str, object]:
    observed = observe_git_effect(root, effect, environment=environment)
    if cast("dict[str, str]", observed["refs"]) != desired:
        message = "git_effect_postcondition_failed"
        raise ValueError(message)
    return observed


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
        require_live_lease(
            root,
            plan,
            environment=environment,
            detached_branch=detached_branch,
            recovering=True,
        )
        return observed, True, ""
    require_plan_prestate(
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
        prestate_repository_id=str(plan.policy.get("prestate_repository_id") or ""),
        prestate_repository_bytes_sha256=str(
            plan.policy.get("prestate_repository_bytes_sha256") or ""
        ),
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
            operation = _ref_operation(plan, ref_name, update)
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
    for nonce in (str(intent["nonce"]) for intent in intents):
        clear_ref_intent(root, nonce)


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


def _compensate_git_effect(
    root: Path,
    plan: TransitionPlan,
    effect: GitEffect,
    intents: list[dict[str, object]],
    *,
    environment: Mapping[str, str] | None,
    cause: BaseException,
) -> None:
    """Reverse one applied CAS exactly or retain its committed recovery intent."""
    reverse = GitEffect(
        updates={
            name: GitRefUpdate(expected=update.desired, desired=update.expected)
            for name, update in effect.updates.items()
        },
        assertions=effect.assertions,
    )
    reverse_intents = _claim_effect_intents(root, plan, reverse, phase="prepared")
    completed = _run_effect_program(root, plan, reverse, environment=environment)
    restored = observe_git_effect(root, reverse, environment=environment)
    expected = {name: update.desired for name, update in reverse.updates.items()}
    observed = cast("dict[str, str]", restored["refs"])
    if completed.returncode or observed != expected:
        _abort_effect_intents(root, reverse, reverse_intents)
        ref_name = next(
            name for name in reverse.updates if observed.get(name) != reverse.updates[name].desired
        )
        message = (
            f"git_effect_partial_effect_uncompensated:{ref_name}"
            f":expected={reverse.updates[ref_name].desired}:observed={observed.get(ref_name, '')}"
        )
        raise ValueError(message) from cause
    _claim_effect_intents(root, plan, reverse, phase="committed")
    _clear_claimed_intents(root, [*intents, *reverse_intents])


def _ref_operation(plan: TransitionPlan, ref_name: str, update: GitRefUpdate) -> str:
    operation = str(plan.policy.get("transition") or plan.policy.get("operation") or "")
    release_ref = f"refs/heads/{plan.policy.get('release_branch') or ''}"
    return (
        "release.mirror"
        if operation in {"candidate.accept", "commit.identity-replace"} and ref_name == release_ref
        else "lane.retire.compensate"
        if operation == "lane.retire" and not set(update.expected) - {"0"}
        else operation
    )


def _effect_environment(
    root: Path, plan: TransitionPlan, effect: GitEffect
) -> dict[str, str] | None:
    operation = str(plan.policy.get("transition") or plan.policy.get("operation") or "")
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
