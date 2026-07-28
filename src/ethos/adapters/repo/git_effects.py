"""Git ref effects — CAS execution, attestation, and ref-worktree synchronization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation

if TYPE_CHECKING:
    from ethos.adapters.admission.closeout_intent.marker import CloseoutTransition

_SHA256_HEX_LENGTH = 64


@dataclass(frozen=True, slots=True)
class GitEffectExecutionRequest:
    """Immutable bindings required to execute one Git effect."""

    issuer: str
    permissions: tuple[str, ...]
    commitment_digest: str
    facts_digest: str
    policy_digest: str
    attestations: tuple[Attestation, ...] = ()


def execute_git_effect(
    root: Path,
    effect: GitEffect,
    request: GitEffectExecutionRequest,
) -> Attestation:
    """Execute, recover, or replay one exact Git ref transaction."""
    issuer = request.issuer
    attestations = request.attestations
    permissions = request.permissions
    commitment_digest = request.commitment_digest
    facts_digest = request.facts_digest
    policy_digest = request.policy_digest
    _require_effect_bindings(
        commitment_digest=commitment_digest,
        facts_digest=facts_digest,
        policy_digest=policy_digest,
    )
    _require_effect_permission(effect, permissions)
    replayed = _replay_git_effect(
        root,
        effect,
        attestations=attestations,
        commitment_digest=commitment_digest,
        facts_digest=facts_digest,
        policy_digest=policy_digest,
    )
    if replayed is not None:
        return replayed
    observed = {ref: _effect_ref(root, ref) for ref in effect.updates}
    if any(_effect_ref(root, ref) != value for ref, value in effect.assertions.items()):
        message = "git_effect_cas_mismatch"
        raise ValueError(message)
    desired = {ref: update.desired for ref, update in effect.updates.items()}
    if observed == desired:
        return _attestation(
            effect,
            issuer=issuer,
            state="recovered",
            commitment_digest=commitment_digest,
            facts_digest=facts_digest,
            policy_digest=policy_digest,
        )
    expected = {ref: update.expected for ref, update in effect.updates.items()}
    if observed != expected:
        message = "git_effect_cas_mismatch"
        raise ValueError(message)
    program = "\0".join(
        (
            "start",
            *(
                token
                for ref, value in effect.assertions.items()
                for token in (f"update {ref}", value, value)
            ),
            *(
                token
                for ref, update in effect.updates.items()
                for token in (f"update {ref}", update.desired, update.expected)
            ),
            "prepare",
            "commit",
            "",
        )
    )
    completed = run_git(root, "update-ref", "--stdin", "-z", check=False, stdin=program)
    if completed.returncode:
        message = "git_effect_cas_rejected"
        raise ValueError(message)
    if {ref: _effect_ref(root, ref) for ref in effect.updates} != desired:
        message = "git_effect_postcondition_failed"
        raise ValueError(message)
    return _attestation(
        effect,
        issuer=issuer,
        state="applied",
        commitment_digest=commitment_digest,
        facts_digest=facts_digest,
        policy_digest=policy_digest,
    )


def _replay_git_effect(
    root: Path,
    effect: GitEffect,
    *,
    attestations: tuple[Attestation, ...],
    commitment_digest: str,
    facts_digest: str,
    policy_digest: str,
) -> Attestation | None:
    digest = effect.digest()
    matching = tuple(
        attestation
        for attestation in attestations
        if attestation.subject == effect.id or attestation.effect_digest == digest
    )
    if not matching:
        return None
    if len(matching) > 1:
        if len({attestation.canonical_json() for attestation in matching}) > 1:
            message = "git_effect_identity_collision"
            raise ValueError(message)
        message = "git_effect_attestation_duplicate"
        raise ValueError(message)
    attestation = matching[0]
    _validate_git_effect_attestation(
        effect,
        attestation,
        commitment_digest=commitment_digest,
        facts_digest=facts_digest,
        policy_digest=policy_digest,
    )
    if any(_effect_ref(root, ref) != value for ref, value in effect.assertions.items()):
        message = "git_effect_cas_mismatch"
        raise ValueError(message)
    if any(_effect_ref(root, ref) != update.desired for ref, update in effect.updates.items()):
        message = "git_effect_postcondition_failed"
        raise ValueError(message)
    return attestation


def _validate_git_effect_attestation(
    effect: GitEffect,
    attestation: Attestation,
    *,
    commitment_digest: str,
    facts_digest: str,
    policy_digest: str,
) -> None:
    if (
        attestation.predicate != "effect:git-ref-update"
        or attestation.subject != effect.id
        or attestation.plan_digest != effect.plan_digest
        or attestation.effect_digest != effect.digest()
    ):
        message = "git_effect_identity_collision"
        raise ValueError(message)
    for name, expected in (
        ("commitment_digest", commitment_digest),
        ("facts_digest", facts_digest),
        ("policy_digest", policy_digest),
    ):
        if getattr(attestation, name) != expected:
            message = f"git_effect_attestation_binding_mismatch:{name}"
            raise ValueError(message)
    if attestation.verdict != "pass":
        message = f"git_effect_attestation_verdict_{attestation.verdict}"
        raise ValueError(message)
    if (
        attestation.statement.get("state") not in {"applied", "recovered"}
        or attestation.statement.get("updates") != effect.model_dump(mode="json")["updates"]
    ):
        message = "git_effect_attestation_content_mismatch"
        raise ValueError(message)


def _require_effect_bindings(
    *,
    commitment_digest: str,
    facts_digest: str,
    policy_digest: str,
) -> None:
    for name, value in (
        ("commitment_digest", commitment_digest),
        ("facts_digest", facts_digest),
        ("policy_digest", policy_digest),
    ):
        if not value:
            message = f"git_effect_binding_missing:{name}"
            raise ValueError(message)
        if len(value) != _SHA256_HEX_LENGTH or any(
            character not in "0123456789abcdef" for character in value
        ):
            message = f"git_effect_binding_invalid:{name}"
            raise ValueError(message)


def _require_effect_permission(effect: GitEffect, permissions: tuple[str, ...]) -> None:
    admitted = set(permissions)
    if "git.ref.compare-and-swap" not in admitted and not set(effect.permissions) <= admitted:
        message = "git_effect_permission_denied"
        raise ValueError(message)


def git_effect_attestations(
    root: Path,
    effect: GitEffect,
    record: Attestation | None = None,
) -> tuple[Attestation, ...]:
    path = Path(git_common_dir(root), "ethos", "git-effects", f"{effect.digest()}.json")
    if record is not None:
        existing = git_effect_attestations(root, effect)
        if existing:
            if existing[0].canonical_json() != record.canonical_json():
                message = "git_effect_attestation_collision"
                raise ValueError(message)
            return existing
        if (
            record.predicate != "effect:git-ref-update"
            or record.subject != effect.id
            or record.plan_digest != effect.plan_digest
            or record.effect_digest != effect.digest()
        ):
            message = "git_effect_attestation_binding_mismatch"
            raise ValueError(message)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.canonical_json(), encoding="utf-8")
        return (record,)
    if not path.exists():
        return ()
    try:
        return (Attestation.model_validate_json(path.read_text(encoding="utf-8")),)
    except (OSError, ValueError) as error:
        message = "git_effect_attestation_invalid"
        raise ValueError(message) from error


def git_ref_effect(
    effect_id: str,
    plan_digest: str,
    transitions: tuple[CloseoutTransition, ...],
    assertions: dict[str, str],
) -> GitEffect:
    """Build one exact ref effect from transition-shaped records."""
    updates = {
        str(item.ref_name): GitRefUpdate(expected=str(item.old_value), desired=str(item.new_value))
        for item in transitions
    }
    return GitEffect(
        id=effect_id,
        plan_digest=plan_digest,
        updates=updates,
        assertions=assertions,
    )


def sync_linked_ref_worktree(
    worktrees: list[dict[str, object]],
    branch: str,
    head: str,
    previous: str,
) -> dict[str, object]:
    """Synchronize a linked ref worktree after its ref transaction."""
    if not branch:
        return {"mode": "independent", "worktree_sync": "not_enabled"}
    path = next(
        (
            Path(str(item["path"]))
            for item in worktrees
            if item.get("branch") == branch
            and item.get("worktree_binding") in {"current", "linked"}
        ),
        None,
    )
    result = {
        "mode": "accepted_ff",
        "branch": branch,
        "previous_head": previous,
        "head": head,
        "worktree_sync": "not_linked" if path is None else "synced",
    }
    if path is None:
        return result
    reset = run_git(path, "reset", "--hard", head, check=False)
    if reset.returncode:
        return {**result, "worktree_sync": "failed", "stderr": reset.stderr.strip()}
    return {
        **result,
        "worktree_sync": (
            "dirty" if run_git(path, "status", "--short", check=False).stdout.strip() else "synced"
        ),
    }


def sync_current_worktree(root: Path, head: str) -> dict[str, object]:
    reset = run_git(root, "reset", "--hard", head, check=False)
    if reset.returncode and any(
        token in reset.stderr.lower() for token in ("index.lock", "could not lock index")
    ):
        reset = run_git(root, "reset", "--hard", head, check=False)
    if reset.returncode:
        return {"state": "failed", "stderr": reset.stderr.strip()}
    status = run_git(root, "status", "--short", check=False)
    return {
        "state": "dirty" if status.returncode or status.stdout.strip() else "synced",
        "status": status.stdout.strip(),
        "stderr": status.stderr.strip(),
    }


def reference_transaction_hook_changed(
    root: Path,
    accepted_head: str,
    candidate_head: str,
) -> bool:
    path = ".githooks/reference-transaction"
    entries = [
        run_git(root, "ls-tree", head, path, check=False).stdout.strip()
        for head in (accepted_head, candidate_head)
    ]
    if not entries[1].startswith("100755 blob "):
        message = "release_mirror_candidate_hook_invalid"
        raise ValueError(message)
    return entries[0] != entries[1]


def _effect_ref(root: Path, ref: str) -> str:
    completed = run_git(root, "rev-parse", "--verify", ref, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _attestation(
    effect: GitEffect,
    *,
    issuer: str,
    state: str,
    commitment_digest: str,
    facts_digest: str,
    policy_digest: str,
) -> Attestation:
    return Attestation.issue(
        {
            "predicate": "effect:git-ref-update",
            "verifier": issuer,
            "subject": effect.id,
            "issued_at": datetime.now(UTC),
            "verdict": "pass",
            "commitment_digest": commitment_digest,
            "facts_digest": facts_digest,
            "plan_digest": effect.plan_digest,
            "policy_digest": policy_digest,
            "effect_digest": effect.digest(),
            "statement": {"state": state, "updates": effect.model_dump(mode="json")["updates"]},
        }
    )
