"""Freshly admit and execute independent peer publication effects."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.publication.observation as publication_observation
import ethos.adapters.repo.git as git
from ethos.adapters.admission.publication import push_admission_report
from ethos.adapters.mutation.proof import proof_admission_report
from ethos.adapters.mutation.publication.attestation import terminal_publication_result
from ethos.adapters.repo.git_object import observe_git_object
from ethos.contracts.publication import PublicationEffect
from ethos.contracts.publication import PublicationSource
from ethos.contracts.publication import PublicationTarget
from ethos.contracts.publication import PublicationUpdate
from ethos.contracts.publication import publication_effect_from_plan
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.release.publication import publication_proof_selection

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan


def _transaction_refs(observation: Mapping[str, object]) -> dict[str, dict[str, object]]:
    """Return one typed peer observation's full-ref mapping."""
    refs = observation.get("refs")
    return cast("dict[str, dict[str, object]]", refs) if isinstance(refs, dict) else {}


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


def apply_remote_publication_effect(*, root: Path, plan: TransitionPlan) -> dict[str, object]:
    """Preflight all peers and freshly admit each independent exact-CAS effect."""
    effect = publication_effect_from_plan(plan)
    authority_verdict, authority_gaps = _publication_authority(root, plan=plan, effect=effect)
    observations = {target.id: _observe_peer(root, target) for target in effect.targets}
    observed = tuple(_peer_admission(target, observations[target.id]) for target in effect.targets)
    gaps = (*authority_gaps, *(gap for _, peer_gaps in observed for gap in peer_gaps))
    verdict = reduce_verdicts(authority_verdict, *(item[0] for item in observed))
    if verdict != "pass":
        return terminal_publication_result(
            root=root,
            plan=plan,
            effect=effect,
            verdict=verdict,
            state="preflight_unknown" if verdict == "unknown" else "preflight_blocked",
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
        observations[target.id] = _observe_peer(root, target)
        peer_verdict, peer_gaps = _peer_admission(target, observations[target.id])
        authority_verdict, authority_gaps = _publication_authority(root, plan=plan, effect=effect)
        verdict = reduce_verdicts(peer_verdict, authority_verdict)
        if verdict != "pass":
            return terminal_publication_result(
                root=root,
                plan=plan,
                effect=effect,
                verdict=verdict,
                state="partial"
                if applied
                else "preflight_unknown"
                if verdict == "unknown"
                else "preflight_blocked",
                required_gaps=tuple(dict.fromkeys((*authority_gaps, *peer_gaps))),
                observations=observations,
                applied=tuple(applied),
                failed="",
                pending=tuple(item.id for item in effect.targets[index:]),
                attempts=tuple(attempts),
            )
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
        post_observed = _observe_peer(root, target)
        observed_refs = _transaction_refs(post_observed)
        post_observation_gaps = tuple(
            f"publication_remote_observation_unavailable:{target.id}:{target.remote}:{target_ref}"
            for target_ref, item in observed_refs.items()
            if item.get("state") == "unavailable"
        )
        if result["state"] == "applied" and post_observation_gaps:
            return terminal_publication_result(
                root=root,
                plan=plan,
                effect=effect,
                verdict="unknown",
                state="outcome_unknown",
                required_gaps=post_observation_gaps,
                observations={**observations, target.id: post_observed},
                applied=tuple(applied),
                failed="",
                pending=tuple(item.id for item in effect.targets[index:]),
                attempts=tuple(attempts),
            )
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
                observations={**observations, target.id: post_observed},
                applied=tuple(applied),
                failed=target.id,
                pending=tuple(item.id for item in effect.targets[index + 1 :]),
                attempts=tuple(attempts),
            )
        applied.append(target.id)
        observations[target.id] = post_observed
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


def _observe_peer(root: Path, target: PublicationTarget) -> dict[str, object]:
    """Read one peer's exact refs through the shared bounded observer."""
    return {
        "kind": "git_remote_transaction_observation",
        "remote": target.remote,
        "state": "observed",
        "refs": {
            update.target_ref: publication_observation.observe_remote_ref(
                root, target.remote, update.target_ref
            )
            for update in target.updates
        },
    }


def _peer_admission(
    target: PublicationTarget, observation: Mapping[str, object]
) -> tuple[Verdict, tuple[str, ...]]:
    """Distinguish unavailable observations from an observed exact-CAS conflict."""
    refs = _transaction_refs(observation)
    unavailable = tuple(
        f"publication_remote_observation_unavailable:{target.id}:{target.remote}:{update.target_ref}"
        for update in target.updates
        if refs[update.target_ref].get("state") == "unavailable"
    )
    drift = tuple(
        f"publication_target_drift:{target.id}:{update.target_ref.removeprefix('refs/heads/')}"
        for update in target.updates
        if refs[update.target_ref].get("state") != "unavailable"
        and refs[update.target_ref].get("object_oid") not in {update.expected, update.desired}
    )
    return "block" if drift else "unknown" if unavailable else "pass", (*unavailable, *drift)


def _publication_authority(
    root: Path, *, plan: TransitionPlan, effect: PublicationEffect
) -> tuple[Verdict, tuple[str, ...]]:
    """Observe source trust and all destination obligations at the effect boundary."""
    admissions = tuple(
        push_admission_report(
            root=root,
            target_ref=update.target_ref,
            pushed_head=update.desired,
            remote_head=update.expected,
            remote_name=target.remote,
        )
        for target in effect.targets
        for update in target.updates
    )
    proof_gaps = _proof_drift_gaps(root, plan=plan, effect=effect, admissions=admissions)
    source_gaps = _source_drift_gaps(
        effect.source,
        observe_git_object(root, effect.source.object_oid, effect.source.kind),
    )
    gaps = tuple(
        dict.fromkeys(
            (
                *proof_gaps,
                *source_gaps,
                *(gap for report in admissions for gap in string_sequence(report["required_gaps"])),
            )
        )
    )
    return reduce_verdicts(
        "block" if proof_gaps or source_gaps else "pass",
        *(report_verdict(report) for report in admissions),
        required_gaps=gaps,
    ), gaps


def _proof_drift_gaps(
    root: Path,
    *,
    plan: TransitionPlan,
    effect: PublicationEffect,
    admissions: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    """Re-select and compare the exact proof bound into the request."""
    roles = {str(report["role"]) for report in admissions}
    required = any(publication_proof_selection(role) != "review_object" for role in roles)
    carried = plan.prior_attestations.get("proof")
    if not required:
        return (
            ()
            if not carried and plan.commitment is None
            else ("publication_review_proof_unexpected",)
        )
    if not isinstance(carried, Mapping) or not carried:
        return ("publication_proof_binding_missing",)
    selection = "repository_transition"
    if carried.get("selection") != selection:
        return ("publication_proof_selection_mismatch",)
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
