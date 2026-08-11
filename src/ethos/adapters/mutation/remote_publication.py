"""Observe, persist, and execute exact-CAS remote publication effects."""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git
from ethos.adapters.mutation.proof_artifacts import persist_attestation
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.publication import RemotePublicationEffect
from ethos.contracts.publication import RemotePublicationTarget
from ethos.contracts.publication import compile_remote_publication_plan
from ethos.contracts.publication import remote_publication_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Facts

if TYPE_CHECKING:
    from ethos.contracts.verdict import Verdict

_ZERO_OID = "0" * 40


def observe_remote_publication_effect(
    *,
    root: Path,
    source_head: str,
    target_ref: str,
    remotes: dict[str, str],
) -> tuple[RemotePublicationEffect | None, dict[str, dict[str, object]], tuple[str, ...]]:
    """Observe every declared target before compiling one immutable effect."""
    observations: dict[str, dict[str, object]] = {}
    targets: list[RemotePublicationTarget] = []
    gaps: list[str] = []
    for peer_id, remote in remotes.items():
        observation = git.remote_ref_observation(root, remote, target_ref)
        observations[peer_id] = observation
        state = str(observation.get("state") or "unavailable")
        if state == "unavailable":
            gaps.append(f"publication_proposal_remote_unavailable:{peer_id}:{remote}")
            continue
        observed = str(observation.get("head") or _ZERO_OID)
        if observed != _ZERO_OID and observed != source_head:
            gaps.append(
                f"publication_proposal_target_drift:{peer_id}:"
                f"{target_ref.removeprefix('refs/heads/')}"
            )
        targets.append(
            RemotePublicationTarget(
                id=peer_id,
                remote=remote,
                target_ref=target_ref,
                expected=observed,
                desired=source_head,
            )
        )
    effect = (
        RemotePublicationEffect.compile(
            repository_common_dir=git.git_common_dir(root),
            source_head=source_head,
            targets=tuple(targets),
        )
        if targets and len(targets) == len(remotes)
        else None
    )
    return effect, observations, tuple(dict.fromkeys(gaps))


def persist_remote_publication_request(root: Path, plan: TransitionPlan) -> dict[str, object]:
    """Persist the exact dry-run TransitionPlan as immutable request bytes."""
    payload = plan.model_dump_json(indent=None).encode()
    digest = hashlib.sha256(payload).hexdigest()
    path = local_state_root(root) / "requests" / "publication" / f"{digest}.json"
    write_content_addressed(path, payload, collision="remote_publication_request_collision")
    return {
        "path": path.as_posix(),
        "sha256": f"sha256:{digest}",
        "size_bytes": path.stat().st_size,
        "media_type": "application/json",
    }


def load_remote_publication_request(
    root: Path, receipt_path: str, receipt_sha256: str
) -> TransitionPlan:
    """Load one request only from this repository's immutable request store."""
    path = Path(receipt_path).expanduser().resolve()
    store = (local_state_root(root) / "requests" / "publication").resolve()
    expected = receipt_sha256.removeprefix("sha256:")
    if not expected or path.parent != store or path.suffix != ".json" or path.stem != expected:
        message = "remote_publication_receipt_path_invalid"
        raise ValueError(message)
    try:
        payload = path.read_bytes()
    except OSError as error:
        message = "remote_publication_receipt_missing"
        raise ValueError(message) from error
    if hashlib.sha256(payload).hexdigest() != expected:
        message = "remote_publication_receipt_sha256_mismatch"
        raise ValueError(message)
    try:
        plan = TransitionPlan.model_validate_json(payload)
        effect = remote_publication_effect_from_plan(plan)
    except ValueError as error:
        message = "remote_publication_receipt_invalid"
        raise ValueError(message) from error
    if effect.repository_common_dir != git.git_common_dir(root):
        message = "remote_publication_receipt_repository_mismatch"
        raise ValueError(message)
    return plan


def compile_remote_publication_request(
    *, root: Path, effect: RemotePublicationEffect
) -> TransitionPlan:
    """Compile fresh remote observations into the common TransitionPlan."""
    commitment = load_repository_commitment(root, tree_ref=effect.source_head)
    facts = Facts(
        repository=commitment.id,
        head=effect.source_head,
        tree=git.current_tree(root, effect.source_head),
        observed_at=datetime.now(UTC),
        values={
            "remote_targets": tuple(target.model_dump(mode="json") for target in effect.targets),
        },
        source_refs=(
            "git:HEAD",
            "git:HEAD^{tree}",
            *(f"git:{target.remote}:{target.target_ref}" for target in effect.targets),
        ),
    )
    return compile_remote_publication_plan(
        commitment=commitment,
        facts=facts,
        effect=effect,
        prior_attestations={},
    )


def apply_remote_publication_effect(*, root: Path, plan: TransitionPlan) -> dict[str, object]:
    """Execute peer-local CAS pushes after a complete fresh preflight."""
    effect = remote_publication_effect_from_plan(plan)
    observations = {
        target.id: git.remote_ref_observation(root, target.remote, target.target_ref)
        for target in effect.targets
    }
    gaps = tuple(
        f"publication_proposal_remote_unavailable:{target.id}:{target.remote}"
        if observations[target.id].get("state") == "unavailable"
        else f"publication_proposal_target_drift:{target.id}:"
        f"{target.target_ref.removeprefix('refs/heads/')}"
        for target in effect.targets
        if observations[target.id].get("state") == "unavailable"
        or observations[target.id].get("head") not in {target.expected, target.desired}
    )
    if gaps:
        return _terminal_result(
            root=root,
            plan=plan,
            effect=effect,
            verdict="block",
            state="preflight_blocked",
            required_gaps=gaps,
            observations=observations,
            applied=(),
            failed="",
            pending=tuple(target.id for target in effect.targets),
            attempts=(),
        )
    applied: list[str] = []
    attempts: list[dict[str, object]] = []
    for index, target in enumerate(effect.targets):
        if observations[target.id].get("head") == target.desired:
            applied.append(target.id)
            attempts.append(
                {
                    "id": target.id,
                    "remote": target.remote,
                    "state": "already_applied",
                    "exit_code": 0,
                    "stderr": "",
                }
            )
            continue
        result = git.push_remote_ref_exact(
            root,
            remote=target.remote,
            target_ref=target.target_ref,
            expected=target.expected,
            desired=target.desired,
        )
        attempts.append({"id": target.id, "remote": target.remote, **result})
        observed = git.remote_ref_observation(root, target.remote, target.target_ref)
        if result["state"] != "applied" or observed.get("head") != target.desired:
            gap = f"publication_proposal_push_failed:{target.id}:{target.remote}"
            return _terminal_result(
                root=root,
                plan=plan,
                effect=effect,
                verdict="block",
                state="partial" if applied else "failed",
                required_gaps=(gap,),
                observations={**observations, target.id: observed},
                applied=tuple(applied),
                failed=target.id,
                pending=tuple(item.id for item in effect.targets[index + 1 :]),
                attempts=tuple(attempts),
            )
        applied.append(target.id)
        observations[target.id] = observed
    return _terminal_result(
        root=root,
        plan=plan,
        effect=effect,
        verdict="pass",
        state="applied",
        required_gaps=(),
        observations=observations,
        applied=tuple(applied),
        failed="",
        pending=(),
        attempts=tuple(attempts),
    )


def _terminal_result(
    *,
    root: Path,
    plan: TransitionPlan,
    effect: RemotePublicationEffect,
    verdict: Verdict,
    state: str,
    required_gaps: tuple[str, ...],
    observations: dict[str, dict[str, object]],
    applied: tuple[str, ...],
    failed: str,
    pending: tuple[str, ...],
    attempts: tuple[dict[str, object], ...],
) -> dict[str, object]:
    statement = {
        "claim": {"operation": effect.operation, "verdict": verdict},
        "plan": plan.model_dump(mode="json"),
        "effect": effect.model_dump(mode="json"),
        "state": state,
        "required_gaps": list(required_gaps),
        "observations": observations,
        "partial_effects": {
            "applied_peers": list(applied),
            "failed_peer": failed,
            "pending_peers": list(pending),
        },
        "attempts": list(attempts),
        "cross_provider_atomicity_claimed": False,
    }
    effect_digest = effect.digest()
    attestation = Attestation.issue(
        {
            "predicate": "publication:remote-effect",
            "verifier": "ethos:remote-publication-executor",
            "subject": f"git:commit:{effect.source_head}",
            "issued_at": datetime.now(UTC),
            "verdict": verdict,
            "commitment_digest": plan.inputs.commitment,
            "facts_digest": plan.inputs.facts,
            "plan_digest": plan.digest,
            "policy_digest": plan.inputs.policy,
            "effect_digest": effect_digest,
            "statement": statement,
            "evidence_refs": tuple(
                f"git:{target.remote}:{target.target_ref}:{target.desired}"
                for target in effect.targets
            ),
        }
    )
    path = persist_attestation(root, attestation)
    payload = path.read_bytes()
    return {
        "state": state,
        "required_gaps": list(required_gaps),
        "observations": observations,
        "partial_effects": statement["partial_effects"],
        "attempts": list(attempts),
        "attestation": {
            "id": attestation.id,
            "path": path.as_posix(),
            "sha256": f"sha256:{hashlib.sha256(payload).hexdigest()}",
        },
    }
