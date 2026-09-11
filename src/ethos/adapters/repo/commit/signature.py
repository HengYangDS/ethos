"""Re-derive signature-only repair evidence from its trusted native prestate."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.commit.admission import commit_policy_report
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_object import commit_payload
from ethos.adapters.repo.git_object import equivalent_commit_identity
from ethos.adapters.repo.git_object import observe_commit
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.worktree_effects import raw_worktree_records
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import strict_branch_role_policy_from_text
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from ethos.repository.policy.commit import commit_policy_from_text

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ethos.contracts.semantic import Attestation

ATTEMPT = "observation:signature-repair-attempt"
RESULT = "effect:commit-signature"


def _require(condition: object, gap: str) -> None:
    if not condition:
        raise ValueError(gap)


def signature_coordinates(root: Path, old: str, actor: str, new: str = "") -> dict[str, object]:
    """Derive allowed refs and identity from an unsigned accepted source, not a receipt."""
    source = observe_commit(root, old)
    _require(source["verdict"] == "pass", "signature_repair_source_unavailable")
    _require(source["object_oid"] == old, "signature_repair_source_not_exact")
    _require(
        not cast("dict[str, object]", source["signature"])["present"],
        "signature_repair_source_not_unsigned",
    )
    policy_text = committed_file_text(root, old, ".ethos/workspace.toml")
    policy = strict_branch_role_policy_from_text(policy_text)
    signing = commit_policy_from_text(policy_text)
    _require(signing is not None and signing.signing_required, "signature_repair_policy_required")
    allowed_heads = {old, new} if new else {old}
    _require(
        ref_head(root, policy.accepted_branch) in allowed_heads,
        "signature_repair_accepted_head_stale",
    )
    refs = {f"refs/heads/{policy.accepted_branch}": old}
    if policy.candidate_branch and ref_head(root, policy.candidate_branch) in allowed_heads:
        refs[f"refs/heads/{policy.candidate_branch}"] = old
    if policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF:
        _require(
            ref_head(root, policy.release_branch) in allowed_heads,
            "signature_repair_release_head_stale",
        )
        refs[f"refs/heads/{policy.release_branch}"] = old
    payload = commit_payload(root, old)
    _require(bool(payload), "signature_repair_payload_unavailable")
    if new:
        _require(equivalent_commit_identity(root, old, new), "signature_repair_payload_changed")
        report = commit_policy_report(root, signing, new, verify_trust=True)
        gaps = cast("list[str]", report["required_gaps"])
        _require(not gaps, gaps[0] if gaps else "")
    return {
        "root": root.as_posix(),
        "repository": repository_identity(root, tree_ref=old),
        "actor": actor,
        "old": old,
        "accepted_branch": policy.accepted_branch,
        "policy_sha256": hashlib.sha256(policy_text.encode()).hexdigest(),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "refs": refs,
        "worktrees": sorted(
            (
                {
                    "path": Path(item["worktree"]).resolve().as_posix(),
                    "branch": item["branch"].removeprefix("refs/heads/"),
                }
                for item in raw_worktree_records(root)
                if item.get("branch") in refs
            ),
            key=lambda item: item["path"],
        ),
    }


def validate_signature_coordinates(
    root: Path, coordinates: Mapping[str, object], actor: str, new: str = ""
) -> None:
    """Require exact trusted-source coordinates, selected refs and clean worktrees."""
    _require(coordinates.get("actor") == actor, "signature_repair_actor_mismatch")
    expected = signature_coordinates(root, str(coordinates.get("old", "")), actor, new)
    _require(
        coordinates == expected,
        "signature_repair_coordinates_mismatch",
    )
    _require(
        run_git(root, "branch", "--show-current").stdout.strip() == coordinates["accepted_branch"],
        "signature_repair_accepted_root_required",
    )
    refs = cast("Mapping[str, str]", coordinates["refs"])
    live = {name: ref_head(root, name) for name in refs}
    _require(live == refs or (new and set(live.values()) == {new}), "signature_repair_ref_drift")
    old = str(coordinates["old"])
    for item in cast("list[dict[str, str]]", expected["worktrees"]):
        gap = worktree_sync_gap(
            root,
            (Path(item["path"]),),
            item["branch"],
            live[f"refs/heads/{item['branch']}"],
            old,
            new or old,
        )
        _require(not gap, f"signature_repair_{gap}:{item['path']}")


def signature_plan(root: Path, coordinates: Mapping[str, object], new: str) -> TransitionPlan:
    """Compile the sole exact signature-repair CAS plan from validated coordinates."""
    effect = GitEffect(
        updates={
            name: GitRefUpdate(expected=old, desired=new)
            for name, old in cast("Mapping[str, str]", coordinates["refs"]).items()
        }
    )
    return compile_observed_git_effect(
        root,
        None,
        effect,
        head=str(coordinates["old"]),
        policy={"operation": "commit.identity-replace", "actor": coordinates["actor"]},
        values={"signature_repair": dict(coordinates), "replacement": new},
    )


def signature_record_coordinates(record: Attestation) -> dict[str, object]:
    """Validate a repair record's complete internal binding before selecting it."""
    coordinates = mutable_json(record.payload.body.get("coordinates"))
    _require(
        isinstance(coordinates, dict)
        and set(coordinates)
        == {
            "root",
            "repository",
            "actor",
            "old",
            "accepted_branch",
            "policy_sha256",
            "payload_sha256",
            "refs",
            "worktrees",
        },
        "signature_repair_evidence_invalid",
    )
    coordinates = cast("dict[str, object]", coordinates)
    digest = canonical_json_digest(coordinates)
    _require(
        record.predicate in {ATTEMPT, RESULT}
        and record.payload.kind == record.predicate
        and record.verdict == "pass"
        and record.verifier == coordinates["actor"]
        and record.subject == f"signature-repair:{digest}"
        and record.facts_digest == digest
        and record.policy_digest == coordinates["policy_sha256"]
        and record.commitment_digest is None
        and record.effect_digest is None,
        "signature_repair_evidence_invalid",
    )
    return coordinates


def validate_signature_result(root: Path, result: Attestation, actor: str) -> TransitionPlan:
    """Recompile a recorded result rather than trusting its hashes or claimed permission."""
    coordinates = signature_record_coordinates(result)
    new = result.payload.body.get("replacement")
    _require(isinstance(new, str) and new, "signature_repair_evidence_invalid")
    validate_signature_coordinates(root, coordinates, actor, cast("str", new))
    plan = TransitionPlan.model_validate(mutable_json(result.payload.body.get("plan")))
    expected = signature_plan(root, coordinates, cast("str", new))
    _require(
        result.predicate == RESULT
        and result.plan_digest == plan.digest == expected.digest
        and result.payload.body.get("plan_digest") == expected.digest
        and plan == expected,
        "signature_repair_plan_mismatch",
    )
    return plan


def observe_signature_effects(
    root: Path, coordinates: Mapping[str, object], new: str
) -> dict[str, object]:
    """Observe native postconditions after an attempt without authorizing another effect."""
    report: dict[str, object] = {
        "signed_object": "unknown",
        "selected_refs": "unknown",
        "refs": {},
        "worktrees": [],
    }
    try:
        if new:
            exists = run_git(root, "cat-file", "-e", f"{new}^{{commit}}", check=False)
            report["signed_object"] = "observed" if not exists.returncode else "unknown"
        old = str(coordinates["old"])
        refs = cast("Mapping[str, str]", coordinates["refs"])
        live = {name: ref_head(root, name) for name in refs}
        report["refs"] = live
        report["selected_refs"] = (
            "observed"
            if new and set(live.values()) == {new}
            else "pending"
            if live == refs
            else "diverged"
        )
        worktrees = []
        report["worktrees"] = worktrees
        for item in cast("list[dict[str, str]]", coordinates["worktrees"]):
            head = live[f"refs/heads/{item['branch']}"]
            gap = worktree_sync_gap(
                root, (Path(item["path"]),), item["branch"], head, old, new or old
            )
            worktrees.append(
                {
                    "path": item["path"],
                    "state": "blocked" if gap else "observed" if head == new else "pending",
                    "gap": gap,
                }
            )
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        report["observation_error"] = str(error)
    return report
