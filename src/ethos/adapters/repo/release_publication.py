"""Publication reads of a release: its proof head, recorded qualification and source baseline."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.commit.provenance import accepted_provenance
from ethos.adapters.repo.commit.signature import completed_signature_repair
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git_object import observe_git_object
from ethos.adapters.repo.release import accepted_release_source
from ethos.adapters.repo.release import immutable_tag_commit
from ethos.adapters.repo.release import release_branch_policy
from ethos.adapters.repo.release import release_provenance
from ethos.adapters.repo.release import release_publication_head
from ethos.adapters.repo.release import release_qualification
from ethos.adapters.repo.release import release_tag_policy
from ethos.adapters.repo.release import require_release
from ethos.repository.release.publication import publication_proof_selection

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.branch.roles import BranchRolePolicy


def release_publication_selection(
    root: Path, refs: tuple[str, ...], head: str
) -> tuple[str, dict[str, object] | None]:
    """Select a tag's proof head as `release_publication_head` does, reading its record once."""
    if not refs or not all(ref.startswith("refs/tags/") for ref in refs):
        return head, None
    tag = ref_head(root, refs[0])
    if not tag:
        return head, None
    try:
        current = ref_head(root, release_branch_policy(root).accepted_branch)
        selected = str(observe_git_object(root, tag, "annotated-tag")["peeled_commit"])
    except ValueError:
        return head, None
    try:
        plan = release_provenance(root, ref=refs[0], oid=tag)
    except ValueError:
        return (current if selected == current else head), None
    if plan is None:
        return current, None
    return selected, release_qualification(plan) if plan.facts.get("head") == selected else None


def publication_source_baseline(
    repo: Path,
    *,
    policy: BranchRolePolicy,
    branch: str,
    role: str,
    proof_head: str,
    remote_head: str,
    target_ref: str = "",
    source_oid: str = "",
) -> tuple[dict[str, object], list[str], str, str, Mapping[str, object] | None]:
    """Resolve one accepted or maintenance source for exact protected publication."""
    release = role in {"release_root", "release_publication"} or (
        target_ref.startswith("refs/tags/") and publication_proof_selection(role) != "review_object"
    )
    initial = remote_head in {"0" * 40, "0" * 64}
    try:
        if target_ref.startswith("refs/tags/"):
            selected = immutable_tag_commit(
                repo, ref=target_ref, old=remote_head, new=source_oid, allow_identical=True
            )
            require_release(selected == proof_head, "release_source_binding_mismatch")
        if release:
            accepted = None
            try:
                accepted = accepted_release_source(
                    repo, proof_head, ref=target_ref, old=remote_head, new=source_oid
                )
            except ValueError as error:
                if str(error) != "accepted_closeout_effect_not_attested":
                    raise
            if target_ref.startswith("refs/tags/"):
                release_tag_policy(repo, proof_head, target_ref.removeprefix("refs/tags/"))
            if accepted is not None:
                qualification = accepted.get("qualification")
                provenance = cast("Mapping[str, object]", accepted["provenance"])
                maintenance = cast("Mapping[str, object]", accepted.get("release", {}))
                base = str(maintenance.get("base") or provenance["previous_head"])
                closeout = (
                    {**maintenance, "candidate_head": proof_head, "provenance": provenance}
                    if maintenance
                    else {
                        "attestation_id": provenance["attestation_id"],
                        "plan_digest": provenance["plan_digest"],
                        "accepted_ref": accepted["accepted_ref"],
                        "accepted_before": base,
                        "remote_head": remote_head,
                        "candidate_head": proof_head,
                        "provenance": provenance,
                    }
                ) | ({"release_qualification": qualification} if qualification else {})
                return (
                    closeout,
                    [],
                    base if initial else "",
                    ("accepted_effect" if maintenance else "accepted_closeout_effect")
                    if initial
                    else "",
                    accepted,
                )
        required = (
            branch == policy.accepted_branch
            or release
            or (initial and publication_proof_selection(role) == "repository_transition")
        )
        if not required:
            return {}, [], "", "", None
        require_release(
            not release
            or release_publication_head(repo, ref=target_ref, new=source_oid) == proof_head,
            "release_source_not_current_accepted",
        )
        accepted_ref = f"refs/heads/{policy.accepted_branch}"
        closeout = accepted_provenance(
            repo,
            accepted_ref=accepted_ref,
            candidate_ref=f"refs/heads/{policy.candidate_branch}",
            head=proof_head,
        )
        if closeout is None:
            repair = completed_signature_repair(repo, new=proof_head)
            require_release(
                repair is not None and accepted_ref in cast("Mapping[str, str]", repair["refs"]),
                "accepted_closeout_effect_not_attested",
            )
            assert repair is not None
            return (
                {
                    "attestation_id": repair["attestation_id"],
                    "plan_digest": repair["plan_digest"],
                    "accepted_ref": accepted_ref,
                    "accepted_before": repair["old"],
                    "candidate_head": proof_head,
                    "operation": "commit.identity-replace",
                },
                [],
                "",
                "",
                None,
            )
        return (
            {
                "attestation_id": closeout.attestation.id,
                "plan_digest": closeout.plan.digest,
                "accepted_ref": accepted_ref,
                "accepted_before": closeout.previous_head,
                "remote_head": remote_head,
                "candidate_head": proof_head,
                "provenance": closeout.projection(),
            },
            [],
            closeout.previous_head if initial else "",
            "accepted_closeout_effect" if initial else "",
            None,
        )
    except (OSError, ValueError) as error:
        return {}, [str(error)], "", "", None
