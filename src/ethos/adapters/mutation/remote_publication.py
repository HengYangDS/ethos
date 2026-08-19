"""Observe, persist, and execute exact-CAS remote publication effects."""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git_object import observe_git_object
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.publication import PublicationEffect
from ethos.contracts.publication import PublicationSource
from ethos.contracts.publication import PublicationTarget
from ethos.contracts.publication import compile_publication_plan
from ethos.contracts.publication import publication_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Facts

if TYPE_CHECKING:
    from ethos.contracts.verdict import Verdict


def _observe_remote_ref(root: Path, remote: str, ref: str) -> dict[str, object]:
    zero = git.zero_oid(root)
    peeled_ref = f"{ref}^{{}}" if ref.startswith("refs/tags/") else ""
    completed = git.run_network_git(
        root,
        "ls-remote",
        remote,
        ref,
        *((peeled_ref,) if peeled_ref else ()),
    )
    if completed.returncode != 0:
        return {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "unavailable",
            "object_oid": "",
            "peeled_commit": "",
            "tree_oid": "",
            "exit_code": completed.returncode,
            "stderr": completed.stderr.strip(),
        }
    rows = tuple(line.split() for line in completed.stdout.splitlines() if line.strip())
    if not rows:
        return {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "absent",
            "object_oid": zero,
            "peeled_commit": zero,
            "tree_oid": zero,
            "exit_code": 0,
            "stderr": "",
        }
    values = {row[1]: row[0] for row in rows if len(row) == 2}
    if len(values) != len(rows) or ref not in values or set(values) - {ref, peeled_ref}:
        return {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "unavailable",
            "object_oid": "",
            "peeled_commit": "",
            "tree_oid": "",
            "exit_code": 1,
            "stderr": "remote_ref_observation_ambiguous",
        }
    return {
        "kind": "git_remote_ref_observation",
        "remote": remote,
        "ref": ref,
        "state": "present",
        "object_oid": values[ref],
        "peeled_commit": values.get(peeled_ref, values[ref]),
        "tree_oid": git.current_tree(root, values.get(peeled_ref, values[ref])),
        "exit_code": 0,
        "stderr": "",
    }


def _push_remote_ref_exact(
    root: Path,
    *,
    remote: str,
    target_ref: str,
    expected: str,
    desired: str,
) -> dict[str, object]:
    lease = f"--force-with-lease={target_ref}:{'' if expected == git.zero_oid(root) else expected}"
    completed = git.run_network_git(
        root,
        "push",
        "--porcelain",
        lease,
        remote,
        f"{desired}:{target_ref}",
    )
    return {
        "state": "applied" if completed.returncode == 0 else "failed",
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def observe_remote_publication_effect(
    *,
    root: Path,
    source_ref: str,
    target_ref: str,
    remotes: dict[str, str],
) -> tuple[PublicationEffect | None, dict[str, dict[str, object]], tuple[str, ...]]:
    """Observe every declared target before compiling one immutable effect."""
    kind = "annotated-tag" if target_ref.startswith("refs/tags/") else "commit"
    source_observation = observe_git_object(root, source_ref, kind)
    source_gaps = tuple(str(gap) for gap in source_observation.get("required_gaps", ()))
    if source_gaps:
        mapped = tuple(
            f"publication_source_not_annotated_tag:{source_ref}"
            if gap == "git_object_kind_mismatch" and kind == "annotated-tag"
            else f"publication_source_signature_untrusted:{source_ref}"
            if gap.startswith("git_object_signature_")
            else f"publication_source_invalid:{source_ref}:{gap}"
            for gap in source_gaps
        )
        return None, {}, mapped
    signature = source_observation.get("signature")
    if not isinstance(signature, dict):
        return None, {}, (f"publication_source_signature_untrusted:{source_ref}",)
    source = PublicationSource.model_validate(
        {
            "kind": kind,
            "object_oid": source_observation["object_oid"],
            "peeled_commit": source_observation["peeled_commit"],
            "tree_oid": source_observation["tree_oid"],
            "signature": {
                "verdict": signature["verdict"],
                "principal": signature["principal"],
                "fingerprint": signature["fingerprint"],
                "trust_anchor_sha256": signature["trust_anchor_sha256"],
                "verifier": signature["verifier"],
                "verifier_version": signature["verifier_version"],
            },
        }
    )
    zero = git.zero_oid(root)
    observations: dict[str, dict[str, object]] = {}
    targets: list[PublicationTarget] = []
    gaps: list[str] = []
    for peer_id, remote in remotes.items():
        observation = _observe_remote_ref(root, remote, target_ref)
        observations[peer_id] = observation
        state = str(observation.get("state") or "unavailable")
        if state == "unavailable":
            gaps.append(f"publication_remote_unavailable:{peer_id}:{remote}")
            continue
        observed = str(observation.get("object_oid") or zero)
        if observed != zero and observed != source.object_oid:
            gaps.append(
                f"publication_target_drift:{peer_id}:{target_ref.removeprefix('refs/heads/')}"
            )
        targets.append(
            PublicationTarget(
                id=peer_id,
                remote=remote,
                target_ref=target_ref,
                expected=observed,
                desired=source.object_oid,
            )
        )
    effect = (
        PublicationEffect.compile(
            repository_common_dir=git.git_common_dir(root),
            source=source,
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
        effect = publication_effect_from_plan(plan)
    except ValueError as error:
        message = "remote_publication_receipt_invalid"
        raise ValueError(message) from error
    if effect.repository_common_dir != git.git_common_dir(root):
        message = "remote_publication_receipt_repository_mismatch"
        raise ValueError(message)
    return plan


def compile_remote_publication_request(*, root: Path, effect: PublicationEffect) -> TransitionPlan:
    """Compile fresh remote observations into the common TransitionPlan."""
    commitment = load_repository_commitment(root, tree_ref=effect.source.peeled_commit)
    facts = Facts(
        repository=commitment.id,
        head=effect.source.peeled_commit,
        tree=effect.source.tree_oid,
        observed_at=datetime.now(UTC),
        values={
            "publication_source": effect.source.model_dump(mode="json"),
            "remote_targets": tuple(target.model_dump(mode="json") for target in effect.targets),
        },
        source_refs=(
            "git:HEAD",
            "git:HEAD^{tree}",
            *(f"git:{target.remote}:{target.target_ref}" for target in effect.targets),
        ),
    )
    return compile_publication_plan(
        commitment=commitment,
        facts=facts,
        effect=effect,
        prior_attestations={},
    )


def apply_remote_publication_effect(*, root: Path, plan: TransitionPlan) -> dict[str, object]:
    """Execute peer-local CAS pushes after a complete fresh preflight."""
    effect = publication_effect_from_plan(plan)
    source_observation = observe_git_object(
        root,
        effect.source.object_oid,
        effect.source.kind,
    )
    source_gaps = _source_drift_gaps(effect.source, source_observation)
    observations = {
        target.id: _observe_remote_ref(root, target.remote, target.target_ref)
        for target in effect.targets
    }
    gaps = (
        *source_gaps,
        *tuple(
            f"publication_remote_unavailable:{target.id}:{target.remote}"
            if observations[target.id].get("state") == "unavailable"
            else f"publication_target_drift:{target.id}:"
            f"{target.target_ref.removeprefix('refs/heads/')}"
            for target in effect.targets
            if observations[target.id].get("state") == "unavailable"
            or observations[target.id].get("object_oid") not in {target.expected, target.desired}
        ),
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
        if observations[target.id].get("object_oid") == target.desired:
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
        result = _push_remote_ref_exact(
            root,
            remote=target.remote,
            target_ref=target.target_ref,
            expected=target.expected,
            desired=target.desired,
        )
        attempts.append({"id": target.id, "remote": target.remote, **result})
        observed = _observe_remote_ref(root, target.remote, target.target_ref)
        parity = (
            observed.get("object_oid") == effect.source.object_oid
            and observed.get("peeled_commit") == effect.source.peeled_commit
            and observed.get("tree_oid") == effect.source.tree_oid
        )
        if result["state"] != "applied" or not parity:
            gap = f"publication_push_failed:{target.id}:{target.remote}"
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


def _source_drift_gaps(
    expected: PublicationSource,
    observed: dict[str, object],
) -> tuple[str, ...]:
    """Return exact local object or trust drift before any remote effect."""
    if observed.get("required_gaps"):
        return ("publication_source_signature_drift",)
    signature = observed.get("signature")
    if not isinstance(signature, dict):
        return ("publication_source_signature_drift",)
    actual = PublicationSource.model_validate(
        {
            "kind": observed["kind"],
            "object_oid": observed["object_oid"],
            "peeled_commit": observed["peeled_commit"],
            "tree_oid": observed["tree_oid"],
            "signature": {
                "verdict": signature["verdict"],
                "principal": signature["principal"],
                "fingerprint": signature["fingerprint"],
                "trust_anchor_sha256": signature["trust_anchor_sha256"],
                "verifier": signature["verifier"],
                "verifier_version": signature["verifier_version"],
            },
        }
    )
    return () if actual == expected else ("publication_source_identity_drift",)


def _terminal_result(
    *,
    root: Path,
    plan: TransitionPlan,
    effect: PublicationEffect,
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
            "schema_version": 2,
            "predicate": "publication:remote-effect",
            "verifier": "ethos:remote-publication-executor",
            "subject": f"git:{effect.source.kind}:{effect.source.object_oid}",
            "issued_at": datetime.now(UTC),
            "valid_from": None,
            "valid_until": None,
            "verdict": verdict,
            "payload": {"kind": "publication:remote-effect", "body": statement},
            "relations": (),
            "advisories": (),
            "commitment_digest": plan.inputs.commitment,
            "facts_digest": plan.inputs.facts,
            "plan_digest": plan.digest,
            "policy_digest": plan.inputs.policy,
            "effect_digest": effect_digest,
            "evidence_refs": tuple(
                sorted(
                    f"git:{target.remote}:{target.target_ref}:{target.desired}"
                    for target in effect.targets
                )
            ),
            "mints_authority": False,
        }
    )
    selected = record_attestations(root, (attestation,))
    return {
        "state": state,
        "required_gaps": list(required_gaps),
        "observations": observations,
        "partial_effects": statement["partial_effects"],
        "attempts": list(attempts),
        "attestation": {
            "id": attestation.id,
            "set_root": selected["root"],
        },
    }
