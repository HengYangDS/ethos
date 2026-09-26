"""Compile and persist exact remote publication requests without granting authority."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from pathlib import Path

import ethos.adapters.mutation.publication.observation as publication_observation
import ethos.adapters.repo.git as git
from ethos.adapters.repo.commit.signature import repaired_peer_ref_provenance
from ethos.adapters.repo.git_object import GitObjectKind
from ethos.adapters.repo.git_object import observe_git_object
from ethos.adapters.repo.git_object import zero_oid
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.release import committed_release_version
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.publication import PublicationEffect
from ethos.contracts.publication import PublicationSource
from ethos.contracts.publication import PublicationTarget
from ethos.contracts.publication import PublicationUpdate
from ethos.contracts.publication import compile_publication_plan
from ethos.contracts.publication import publication_effect_from_plan
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.repository.release.publication import publication_ref_transition
from ethos.repository.release.publication import publication_source_version_gaps


def observe_remote_publication_effect(
    *,
    root: Path,
    source_ref: str,
    target_refs: tuple[str, ...],
    remotes: dict[str, str],
    ref_admissions: dict[str, dict[str, object]],
    retire: bool = False,
) -> tuple[PublicationEffect | None, dict[str, dict[str, object]], tuple[str, ...]]:
    """Observe every declared target before compiling one immutable effect."""
    ref_kinds = {
        "annotated-tag" if target_ref.startswith("refs/tags/") else "commit"
        for target_ref in target_refs
    }
    if not target_refs or len(ref_kinds) != 1:
        return None, {}, ("publication_target_ref_kind_mismatch",)
    kind: GitObjectKind = "annotated-tag" if ref_kinds == {"annotated-tag"} else "commit"
    source_observation = observe_git_object(root, source_ref, kind)
    raw_source_gaps = source_observation.get("required_gaps")
    source_gaps = (
        tuple(str(gap) for gap in raw_source_gaps)
        if isinstance(raw_source_gaps, (list, tuple))
        else ()
    )
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
    version_gaps = _version_gaps(root, source_ref, kind, str(source_observation["peeled_commit"]))
    if version_gaps:
        return None, {}, version_gaps
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
    zero = zero_oid(root)
    observations: dict[str, dict[str, object]] = {}
    targets: list[PublicationTarget] = []
    gaps: list[str] = []
    for peer_id, remote in remotes.items():
        ref_observations = publication_observation.observe_remote_refs(root, remote, target_refs)
        unavailable = any(
            str(observation.get("state") or "unavailable") == "unavailable"
            for observation in ref_observations.values()
        )
        observations[peer_id] = {
            "kind": "git_remote_transaction_observation",
            "remote": remote,
            "state": "unavailable" if unavailable else "observed",
            "refs": ref_observations,
        }
        if unavailable:
            gaps.extend(
                f"publication_remote_observation_unavailable:{peer_id}:{remote}:{target_ref}"
                for target_ref, observation in ref_observations.items()
                if observation.get("state") == "unavailable"
            )
            continue
        updates = []
        for target_ref, observation in ref_observations.items():
            observed = str(observation["object_oid"])
            admission = ref_admissions.get(target_ref, {})
            advancing_branch = (
                admission.get("ref_kind") == "branch"
                and admission.get("remote_mutation_allowed") is True
                and observed not in {zero, source.object_oid}
            )
            fast_forward = advancing_branch and git.is_ancestor(
                root, observed, source.peeled_commit
            )
            repaired = (
                advancing_branch
                and not fast_forward
                and repaired_peer_ref_provenance(
                    root, ref=target_ref, old=observed, new=source.object_oid
                )
                is not None
            )
            transition = publication_ref_transition(
                admission,
                observed=observed,
                desired=source.object_oid,
                zero=zero,
                fast_forward=fast_forward,
                repaired=repaired,
            )
            if not retire and transition["effect_allowed"] is not True:
                gaps.append(
                    f"publication_target_drift:{peer_id}:{target_ref.removeprefix('refs/heads/')}"
                )
            updates.append(
                PublicationUpdate(
                    target_ref=target_ref,
                    expected=observed,
                    desired=zero if retire else source.object_oid,
                )
            )
        targets.append(
            PublicationTarget(
                id=peer_id,
                remote=remote,
                updates=tuple(updates),
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


def compile_remote_publication_request(
    *, root: Path, effect: PublicationEffect, proof: dict[str, object]
) -> TransitionPlan:
    """Compile fresh remote observations into the common TransitionPlan."""
    commitment_payload = proof.get("commitment")
    commitment = (
        Commitment.model_validate(commitment_payload, strict=False)
        if isinstance(commitment_payload, Mapping)
        else None
    )
    if proof.get("commitment_digest") != (commitment.digest() if commitment is not None else None):
        message = "publication_proof_commitment_mismatch"
        raise ValueError(message)
    facts = Facts(
        repository=repository_identity(root, tree_ref=effect.source.peeled_commit),
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
            *(
                f"git:{target.remote}:{update.target_ref}"
                for target in effect.targets
                for update in target.updates
            ),
        ),
    )
    return compile_publication_plan(
        commitment=commitment,
        facts=facts,
        effect=effect,
        prior_attestations={"proof": proof} if proof else {},
    )


def observe_publication_request(
    root: Path,
    receipt_path: str,
    receipt_sha256: str,
) -> tuple[TransitionPlan | None, PublicationEffect | None, tuple[str, ...], list[str]]:
    """Resolve receipt contents before any consumer selects destination obligations."""
    try:
        plan = load_remote_publication_request(root, receipt_path, receipt_sha256)
        effect = publication_effect_from_plan(plan)
    except ValueError as error:
        return None, None, (), [str(error)]
    refs = tuple(
        dict.fromkeys(update.target_ref for target in effect.targets for update in target.updates)
    )
    return plan, effect, refs, []


def _version_gaps(root: Path, source_ref: str, kind: GitObjectKind, head: str) -> tuple[str, ...]:
    """Observe native version once for tag publication, not ordinary branch delivery."""
    if kind != "annotated-tag":
        return ()
    try:
        text = committed_release_version(root, head)["version"] + "\n"
    except ValueError as error:
        return (str(error),)
    return publication_source_version_gaps(
        source_ref=source_ref, annotated_tag=True, version_text=text
    )
