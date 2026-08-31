"""Observe, persist, and execute exact-CAS remote publication effects."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import cast

import ethos.adapters.repo.git as git
from ethos.adapters.mutation.proof import proof_admission_report
from ethos.adapters.mutation.publication.attestation import terminal_publication_result
from ethos.adapters.repo.git_object import GitObjectKind
from ethos.adapters.repo.git_object import observe_git_object
from ethos.adapters.repo.git_object import zero_oid
from ethos.adapters.repo.profile import repository_identity
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


def _observe_remote_ref(root: Path, remote: str, ref: str) -> dict[str, object]:
    zero = zero_oid(root)
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


def _transaction_refs(observation: Mapping[str, object]) -> dict[str, dict[str, object]]:
    """Return one typed peer observation's full-ref mapping."""
    refs = observation.get("refs")
    return cast("dict[str, dict[str, object]]", refs) if isinstance(refs, dict) else {}


def _transaction_unavailable(observation: Mapping[str, object]) -> bool:
    """Return whether any ref in one peer transaction is unavailable."""
    return any(
        item.get("state") == "unavailable" for item in _transaction_refs(observation).values()
    )


def _push_remote_ref_set_exact(
    root: Path,
    *,
    remote: str,
    updates: tuple[PublicationUpdate, ...],
) -> dict[str, object]:
    leases = tuple(
        f"--force-with-lease={update.target_ref}:{update.expected}" for update in updates
    )
    refspecs = tuple(f"{update.desired}:{update.target_ref}" for update in updates)
    completed = git.run_network_git(
        root,
        "push",
        "--porcelain",
        "--atomic",
        *leases,
        remote,
        *refspecs,
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
    target_refs: tuple[str, ...],
    remotes: dict[str, str],
    ref_admissions: dict[str, dict[str, object]],
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
    version_observation = (
        git.run_git(
            root,
            "show",
            f"{source_observation['peeled_commit']}:VERSION",
            check=False,
            observation=True,
        )
        if kind == "annotated-tag"
        else None
    )
    if version_gaps := publication_source_version_gaps(
        source_ref=source_ref,
        annotated_tag=kind == "annotated-tag",
        version_text=(
            version_observation.stdout
            if version_observation is not None and version_observation.returncode == 0
            else None
        ),
    ):
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
        ref_observations = {
            target_ref: _observe_remote_ref(root, remote, target_ref) for target_ref in target_refs
        }
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
            gaps.append(f"publication_remote_unavailable:{peer_id}:{remote}")
            continue
        updates = []
        for target_ref, observation in ref_observations.items():
            observed = str(observation.get("object_oid") or zero)
            transition = publication_ref_transition(
                ref_admissions.get(target_ref, {}),
                observed=observed,
                desired=source.object_oid,
                zero=zero,
                fast_forward=(
                    observed not in {zero, source.object_oid}
                    and git.is_ancestor(root, observed, source.peeled_commit)
                ),
            )
            if transition["effect_allowed"] is not True:
                gaps.append(
                    f"publication_target_drift:{peer_id}:{target_ref.removeprefix('refs/heads/')}"
                )
            updates.append(
                PublicationUpdate(
                    target_ref=target_ref,
                    expected=observed,
                    desired=source.object_oid,
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
        prior_attestations={"proof": proof},
    )


def apply_remote_publication_effect(*, root: Path, plan: TransitionPlan) -> dict[str, object]:
    """Execute peer-local CAS pushes after a complete fresh preflight."""
    effect = publication_effect_from_plan(plan)
    proof_gaps = _proof_drift_gaps(root, plan=plan, effect=effect)
    source_observation = observe_git_object(
        root,
        effect.source.object_oid,
        effect.source.kind,
    )
    source_gaps = _source_drift_gaps(effect.source, source_observation)
    observations: dict[str, dict[str, object]] = {
        target.id: {
            "kind": "git_remote_transaction_observation",
            "remote": target.remote,
            "state": "observed",
            "refs": {
                update.target_ref: _observe_remote_ref(root, target.remote, update.target_ref)
                for update in target.updates
            },
        }
        for target in effect.targets
    }
    gaps = (
        *proof_gaps,
        *source_gaps,
        *tuple(
            f"publication_remote_unavailable:{target.id}:{target.remote}"
            if _transaction_unavailable(observations[target.id])
            else f"publication_target_drift:{target.id}:"
            f"{update.target_ref.removeprefix('refs/heads/')}"
            for target in effect.targets
            for update in target.updates
            if _transaction_unavailable(observations[target.id])
            or _transaction_refs(observations[target.id])[update.target_ref].get("object_oid")
            not in {update.expected, update.desired}
        ),
    )
    if gaps:
        return terminal_publication_result(
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
        current_refs = _transaction_refs(observations[target.id])
        if all(
            current_refs[update.target_ref].get("object_oid") == update.desired
            for update in target.updates
        ):
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
        result = _push_remote_ref_set_exact(
            root,
            remote=target.remote,
            updates=target.updates,
        )
        attempts.append({"id": target.id, "remote": target.remote, **result})
        observed_refs = {
            update.target_ref: _observe_remote_ref(root, target.remote, update.target_ref)
            for update in target.updates
        }
        observed: dict[str, object] = {
            "kind": "git_remote_transaction_observation",
            "remote": target.remote,
            "state": "observed",
            "refs": observed_refs,
        }
        parity = all(
            item.get("object_oid") == effect.source.object_oid
            and item.get("peeled_commit") == effect.source.peeled_commit
            and item.get("tree_oid") == effect.source.tree_oid
            for item in observed_refs.values()
        )
        if result["state"] != "applied" or not parity:
            gap = f"publication_push_failed:{target.id}:{target.remote}"
            return terminal_publication_result(
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
    return terminal_publication_result(
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


def _proof_drift_gaps(
    root: Path,
    *,
    plan: TransitionPlan,
    effect: PublicationEffect,
) -> tuple[str, ...]:
    """Re-select and compare the exact proof bound into the request."""
    carried = plan.prior_attestations.get("proof")
    if not isinstance(carried, Mapping) or not carried:
        return ("publication_proof_binding_missing",)
    selection = str(carried.get("selection") or "")
    report = proof_admission_report(
        root,
        effect.source.peeled_commit,
        repository_transition=selection == "repository_transition",
    )
    raw_gaps = report.get("required_gaps")
    gaps = tuple(str(gap) for gap in raw_gaps) if isinstance(raw_gaps, (list, tuple)) else ()
    if gaps:
        return gaps
    current = report.get("attestation")
    if not isinstance(current, Mapping):
        return ("publication_proof_binding_missing",)
    return (
        () if {**current, "selection": selection} == dict(carried) else ("publication_proof_drift",)
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
