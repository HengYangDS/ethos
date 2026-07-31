"""Git ref effects — CAS execution, attestation, and ref-worktree synchronization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.repo.git_effect_attestation
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation

if TYPE_CHECKING:
    from ethos.adapters.admission.closeout_intent.marker import CloseoutTransition

_SHA256_HEX_LENGTH = 64
_REPOSITORY_IDENTITY_MISMATCH = "git_effect_repository_identity_mismatch"
_ZERO_OIDS = {"0" * 40, "0" * 64, ""}


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
        issuer=issuer,
        attestations=attestations,
        commitment_digest=commitment_digest,
        facts_digest=facts_digest,
        policy_digest=policy_digest,
    )
    if replayed is not None:
        return replayed
    before = _observation(root, effect, datetime.now(UTC))
    repository = _effect_repository(root, effect, before)
    observed = {ref: _effect_ref(root, ref) for ref in effect.updates}
    if any(_effect_ref(root, ref) != value for ref, value in effect.assertions.items()):
        message = "git_effect_cas_mismatch"
        raise ValueError(message)
    desired = {ref: update.desired for ref, update in effect.updates.items()}
    if observed == desired:
        return ethos.adapters.repo.git_effect_attestation.issue(
            effect,
            issuer=issuer,
            evidence=(
                repository,
                "recovered",
                before,
                _observation(root, effect, datetime.now(UTC)),
            ),
            commitment_digest=commitment_digest,
            facts_digest=facts_digest,
            policy_digest=policy_digest,
        )
    expected = {ref: update.expected for ref, update in effect.updates.items()}
    if observed != expected:
        message = "git_effect_cas_mismatch"
        raise ValueError(message)
    program = ethos.adapters.repo.git_effect_attestation.transaction_program(effect)
    completed = run_git(root, "update-ref", "--stdin", "-z", check=False, stdin=program)
    if completed.returncode:
        message = "git_effect_cas_rejected"
        raise ValueError(message)
    if {ref: _effect_ref(root, ref) for ref in effect.updates} != desired:
        message = "git_effect_postcondition_failed"
        raise ValueError(message)
    return ethos.adapters.repo.git_effect_attestation.issue(
        effect,
        issuer=issuer,
        evidence=(
            repository,
            "applied",
            before,
            _observation(root, effect, datetime.now(UTC)),
        ),
        commitment_digest=commitment_digest,
        facts_digest=facts_digest,
        policy_digest=policy_digest,
    )


def _replay_git_effect(
    root: Path,
    effect: GitEffect,
    *,
    issuer: str,
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
    ethos.adapters.repo.git_effect_attestation.validate(
        root,
        effect,
        attestation,
        issuer=issuer,
        bindings=(commitment_digest, facts_digest, policy_digest),
    )
    if any(_effect_ref(root, ref) != value for ref, value in effect.assertions.items()):
        message = "git_effect_cas_mismatch"
        raise ValueError(message)
    if any(_effect_ref(root, ref) != update.desired for ref, update in effect.updates.items()):
        message = "git_effect_postcondition_failed"
        raise ValueError(message)
    return attestation


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
        ethos.adapters.repo.git_effect_attestation.validate(
            root,
            effect,
            record,
            issuer=record.verifier,
            bindings=(record.commitment_digest, record.facts_digest, record.policy_digest),
        )
        existing = git_effect_attestations(root, effect)
        if existing:
            if existing[0].canonical_json() != record.canonical_json():
                message = "git_effect_attestation_collision"
                raise ValueError(message)
            return existing
        payload = record.canonical_json().encode("utf-8")
        write_content_addressed(path, payload, collision="git_effect_attestation_collision")
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


def _observation(root: Path, effect: GitEffect, observed_at: datetime) -> dict[str, object]:
    head = current_tracked_head(root)
    return {
        "observed_at": observed_at.isoformat(),
        "head": head,
        "tree": current_tree(root, head),
        "refs": {ref: _effect_ref(root, ref) for ref in effect.updates},
        "assertions": {ref: _effect_ref(root, ref) for ref in effect.assertions},
    }


def _effect_repository(root: Path, effect: GitEffect, before: dict[str, object]) -> str:
    before_refs = before.get("refs")
    before_assertions = before.get("assertions")
    observed = (
        (
            *(str(value) for value in before_refs.values()),
            *(str(value) for value in before_assertions.values()),
        )
        if isinstance(before_refs, dict) and isinstance(before_assertions, dict)
        else ()
    )
    revisions = {
        str(before["head"]),
        *observed,
        *(update.expected for update in effect.updates.values()),
        *(update.desired for update in effect.updates.values()),
        *effect.assertions.values(),
    } - _ZERO_OIDS
    try:
        identities = {
            load_repository_commitment(root, tree_ref=revision).id for revision in revisions
        }
    except ValueError as error:
        raise ValueError(_REPOSITORY_IDENTITY_MISMATCH) from error
    if len(identities) != 1:
        raise ValueError(_REPOSITORY_IDENTITY_MISMATCH)
    return identities.pop()
