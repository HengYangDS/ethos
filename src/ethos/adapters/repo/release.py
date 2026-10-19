"""Observe exact accepted release subjects and their native version materials."""

from __future__ import annotations

import json
import shlex
import tomllib
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.commit.admission import commit_policy_for_revision
from ethos.adapters.repo.commit.admission import commit_policy_report
from ethos.adapters.repo.commit.integration import validate_replayed_commits
from ethos.adapters.repo.commit.provenance import accepted_provenance
from ethos.adapters.repo.commit.provenance import lane_creation_boundary
from ethos.adapters.repo.commit.signature import completed_signature_repair
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import recover_plan
from ethos.adapters.repo.git_object import observe_git_object
from ethos.adapters.repo.git_object import zero_oid
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.branch.roles import strict_branch_role_policy_from_release_text
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.value import mutable_json
from ethos.repository.release.changelog import changelog_errors
from ethos.repository.release.changelog import semver_from_text
from ethos.repository.release.configuration import release_config_from_text
from ethos.repository.release.publication import publication_proof_selection
from ethos.repository.release.publication import publication_ref_role

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.branch.roles import BranchRolePolicy
    from ethos.contracts.plan import TransitionPlan


def require_release(condition: object, gap: str) -> None:
    """Require one precise release invariant without converting unknown into success."""
    if not condition:
        raise ValueError(gap)


def release_branch_policy(root: Path) -> BranchRolePolicy:
    """Keep release roles anchored to current accepted policy, not candidate edits."""
    policy = load_branch_role_policy(root)
    committed = strict_branch_role_policy_from_release_text(
        committed_file_text(root, ref_head(root, policy.accepted_branch), ".ethos/release.toml")
    )
    require_release(policy == committed, "release_branch_policy_changed")
    return policy


def release_selection_command(
    root: Path,
    *,
    head: str,
    previous: str,
    base: str = "",
    tag: str = "",
    apply: bool = False,
    identity_transition: bool = False,
) -> str:
    """Render one exact release selection; a hook requests preview, never authority."""
    return shlex.join(
        (
            "ethos",
            "land",
            "--release",
            "--expect-head",
            head,
            "--release-head",
            previous,
            *(("--release-base", base) if base else ()),
            *(("--tag", tag) if tag else ()),
            *(("--identity-transition",) if identity_transition else ()),
            *(("--apply", "--authorize") if apply else ()),
            "--root",
            str(root),
            "--json",
        )
    )


def _version_value(name: str, raw: str) -> str:
    """Decode native version fields, not lockfiles or arbitrary string occurrences."""
    if name == "VERSION":
        return semver_from_text(raw)
    payload = json.loads(raw) if name.endswith(".json") else tomllib.loads(raw)
    require_release(isinstance(payload, dict), "release_version_source_not_object")
    source = payload if name.endswith(".json") else payload.get("project", {})
    require_release(isinstance(source, dict), "release_version_source_not_object")
    if "version" not in source:
        return ""
    require_release("version" not in source.get("dynamic", ()), "release_version_source_dynamic")
    value = source["version"]
    require_release(isinstance(value, str), "release_version_source_not_text")
    return semver_from_text(value + "\n")


def committed_release_version(root: Path, revision: str) -> dict[str, str]:
    """Resolve committed version inputs and reject conflicting native owners."""
    listed = run_git(
        root,
        "ls-tree",
        "-z",
        revision,
        "--",
        "VERSION",
        "package.json",
        "pyproject.toml",
        text=False,
        check=False,
    )
    require_release(not listed.returncode, "release_version_source_unreadable")
    values = {}
    for entry in filter(None, listed.stdout.split(b"\0")):
        metadata, raw_path = entry.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        name = raw_path.decode()
        gap = f"release_version_source_invalid:{name}"
        require_release(mode in {b"100644", b"100755"} and kind == b"blob", gap)
        raw = run_git(root, "cat-file", "blob", oid.decode()).stdout
        try:
            value = _version_value(name, raw)
        except (TypeError, ValueError) as error:
            raise ValueError(gap) from error
        if value:
            values[name] = value
    require_release(values, "release_version_source_missing")
    require_release(len(set(values.values())) == 1, "release_version_source_ambiguous")
    return {"version": next(iter(values.values())), "source": ",".join(sorted(values))}


def declared_release_tag(root: Path, ref: str) -> bool:
    """Select only the release tags declared by current committed policy."""
    policy = release_branch_policy(root)
    declaration = release_config_from_text(
        committed_file_text(root, ref_head(root, policy.accepted_branch), ".ethos/release.toml")
    )
    tags = tuple(declaration.get("protected_refs", {}).get("tags", ()))
    return bool(publication_ref_role(policy, ref, tags)[2])


def release_tag_policy(root: Path, head: str, name: str) -> dict[str, str]:
    """Bind a requested tag to exact committed declaration and native version."""
    require_release(declared_release_tag(root, f"refs/tags/{name}"), "release_tag_not_declared")
    version = committed_release_version(root, head)
    require_release(name == f"v{version['version']}", "release_tag_version_mismatch")
    if errors := changelog_errors(
        committed_file_text(root, head, "CHANGELOG.md"), target=version["version"]
    ):
        raise ValueError(errors[0])
    return version


def accepted_release_source(
    root: Path, head: str, *, base: str = "", ref: str = "", old: str = "", new: str = ""
) -> dict[str, object]:
    """Validate exact accepted content without claiming historical signatures."""
    policy = release_branch_policy(root)
    accepted_ref = f"refs/heads/{policy.accepted_branch}"
    current = ref_head(root, accepted_ref)
    plan = (
        release_provenance(root, ref=ref, oid=new) if ref.startswith("refs/tags/") and new else None
    )
    maintenance = (
        str(plan.facts.get("values", {}).get("release_request", {}).get("base") or "")
        if plan
        else ""
    )
    if ref.startswith("refs/tags/") and new:
        tag = observe_git_object(root, new, "annotated-tag")
        require_release(
            not tag["required_gaps"] and tag["peeled_commit"] == head,
            "release_tag_source_untrusted",
        )
        require_release(head == current or plan is not None or base, "release_tag_source_untrusted")
    if maintenance:
        assert plan is not None
        require_release(plan.facts.get("head") == head, "release_maintenance_source_mismatch")
        require_release(not base or base == maintenance, "release_base_not_exact_ancestor")
        base = maintenance
    require_release(
        bool(base) or head == current or plan is not None,
        "release_source_not_current_accepted",
    )
    if base:
        require_release(
            ref_head(root, base) == base and is_ancestor(root, base, head),
            "release_base_not_exact_ancestor",
        )
        require_release(
            not observe_git_object(root, base, "commit")["required_gaps"],
            "release_base_signature_untrusted",
        )
        commit_policy = commit_policy_for_revision(root, current)
        gaps = list(
            cast(
                "list[str]",
                commit_policy_report(root, commit_policy, base, verify_trust=False)[
                    "required_gaps"
                ],
            )
        )
        gaps += validate_replayed_commits(
            root,
            baseline_commit=base,
            proposed_commit=head,
            policy=commit_policy,
        )
        require_release(not gaps, gaps[0] if gaps else "")
    source = observe_git_object(root, head, "commit")
    require_release(not source["required_gaps"], "release_source_signature_untrusted")
    closeout = accepted_provenance(
        root,
        accepted_ref=accepted_ref,
        candidate_ref=f"refs/heads/{policy.candidate_branch}",
        head=base or head,
    )
    require_release(closeout is not None, "accepted_closeout_effect_not_attested")
    assert closeout is not None
    accepted_effect = closeout.attestation.model_dump(mode="json")
    if maintenance:
        assert plan is not None
        require_release(
            mutable_json(plan.prior_attestations["accepted_effect"]) == accepted_effect,
            "release_maintenance_accepted_evidence_changed",
        )
    return {
        "accepted_ref": accepted_ref,
        "head": head,
        **({"base": base} if base else {}),
        "accepted_effect": accepted_effect,
        "accepted_plan": closeout.plan.digest,
        "provenance": closeout.projection(),
        "source": source,
        **({"publication": {"ref": ref, "old": old, "new": new}} if ref else {}),
        **(
            {
                "release": {
                    "plan_digest": plan.digest,
                    "operation": "release.promote",
                    "base": base,
                    "proof_attestation_id": str(plan.prior_attestations["proof"]["id"]),
                }
            }
            if maintenance and plan is not None
            else {}
        ),
    }


def accepted_delivery_report(
    root: Path,
    *,
    head: str,
    proposed: str,
    target: str,
    remote_head: str,
    remote: str,
    source: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Describe accepted-content reuse without pretending the remote is accepted.

    No contribution range is introduced at this boundary. Current source trust,
    accepted effect and policy remain independently checked.
    """
    try:
        accepted = (
            source
            if source is not None
            else accepted_release_source(root, head, ref=target, old=remote_head, new=proposed)
        )
        require_release(
            accepted.get("head") == head
            and accepted.get("publication") == {"ref": target, "old": remote_head, "new": proposed},
            "release_source_binding_mismatch",
        )
        policy = commit_policy_for_revision(root, head)
    except (OSError, TypeError, ValueError) as error:
        return {"verdict": "block", "required_gaps": [str(error)]}
    return {
        "verdict": "pass",
        "state": "accepted_content",
        "update_kind": "accepted",
        "target_ref": target,
        "remote_name": remote,
        "remote_head": remote_head,
        "proposed_head": proposed,
        "proposed_commit": head,
        "baseline_commit": head,
        "baseline_ref": accepted["accepted_ref"],
        "baseline_source": "accepted_effect",
        "accepted_plan": accepted["accepted_plan"],
        "accepted_provenance": accepted["provenance"],
        "policy": policy.projection(),
        "revisions": [],
        "checked_commit_count": 0,
        "violations": [],
        "required_gaps": [],
        "signature_verification": "accepted_source_only",
        "history_signature_claimed": False,
    }


def release_ref_subject(
    root: Path, *, ref: str, old: str, new: str, allow_identical: bool = False, base: str = ""
) -> str:
    """Require native release identity; callers separately admit proof and intent."""
    policy = release_branch_policy(root)
    accepted_head = ref_head(root, policy.accepted_branch)
    head = accepted_head
    if ref.startswith("refs/tags/"):
        selected = _immutable_tag_commit(
            root, ref=ref, old=old, new=new, allow_identical=allow_identical
        )
        if selected != head and not allow_identical and not base:
            base = lane_creation_boundary(root, selected)
            require_release(base, "release_tag_source_untrusted")
        head = selected
        release_tag_policy(root, head, ref.removeprefix("refs/tags/"))
    else:
        require_release(new == head, "release_source_not_current_accepted")
        require_release(
            old == zero_oid(root) or is_ancestor(root, old, new), "release_not_fast_forward"
        )
    accepted_release_source(
        root,
        head,
        base=base,
        ref=ref if allow_identical else "",
        new=new if allow_identical else "",
    )
    require_release(
        ref_head(root, policy.accepted_branch) == accepted_head,
        "release_source_not_current_accepted",
    )
    return head


def release_provenance(root: Path, *, ref: str, oid: str) -> TransitionPlan | None:
    """Read the original completed tag-only effect, never a new acceptance registry."""
    plan = recover_plan(
        root,
        operation="release.promote",
        desired=oid,
        ref_name=ref,
        current_postconditions=False,
    )
    if plan is None:
        return None
    effect = git_effect_from_plan(plan)
    update = effect.updates.get(ref)
    require_release(
        ref.startswith("refs/tags/")
        and update is not None
        and (update.expected, update.desired) == (zero_oid(root), oid),
        "release_tag_source_untrusted",
    )
    if plan.facts.get("values", {}).get("release_request", {}).get("base"):
        require_release(set(effect.updates) == {ref}, "release_maintenance_effect_invalid")
    else:
        policy = release_branch_policy(root)
        source = observe_git_object(root, oid, "annotated-tag")
        released = str(source["peeled_commit"])
        require_release(
            not source["required_gaps"]
            and effect.assertions.get(f"refs/heads/{policy.accepted_branch}") == released
            and plan.facts.get("head") == released
            and is_ancestor(root, released, ref_head(root, policy.accepted_branch)),
            "release_tag_source_untrusted",
        )
    return plan


def release_publication_head(root: Path, *, ref: str = "", new: str = "") -> str:
    """Select the exact attested release source; arbitrary historical tags grant nothing."""
    policy = release_branch_policy(root)
    current = ref_head(root, policy.accepted_branch)
    if not ref.startswith("refs/tags/") or not new:
        return current
    source = observe_git_object(root, new, "annotated-tag")
    selected = str(source["peeled_commit"])
    if selected == current:
        return current
    plan = release_provenance(root, ref=ref, oid=new)
    return selected if plan is not None else current


def publication_proof_head(root: Path, refs: tuple[str, ...], head: str) -> str:
    """Prove a tag's release commit; every other publication proves the checkout head."""
    if not refs or not all(ref.startswith("refs/tags/") for ref in refs):
        return head
    tag = ref_head(root, refs[0])
    try:
        return release_publication_head(root, ref=refs[0], new=tag) if tag else head
    except ValueError:
        return head


def _immutable_tag_commit(
    root: Path, *, ref: str, old: str, new: str, allow_identical: bool
) -> str:
    """Validate signature, native header and immutable identity for any admitted tag."""
    source = observe_git_object(root, new, "annotated-tag")
    require_release(not source["required_gaps"], "release_tag_source_untrusted")
    header = run_git(root, "cat-file", "tag", new).stdout.partition("\n\n")[0]
    names = [line.removeprefix("tag ") for line in header.splitlines() if line.startswith("tag ")]
    require_release(names == [ref.removeprefix("refs/tags/")], "release_tag_name_mismatch")
    require_release(
        old == zero_oid(root) or (allow_identical and old == new), "release_tag_immutable"
    )
    return str(source["peeled_commit"])


def release_checkout_gaps(root: Path, head: str, *, base: str = "") -> list[str]:
    """Require the exact clean accepted checkout before local release effects."""
    policy = release_branch_policy(root)
    branch = current_branch(root)
    selected = (
        policy.role_for_branch(branch) == "work_lane" if base else branch == policy.accepted_branch
    )
    if not selected or current_tracked_head(root) != head:
        return ["release_accepted_root_required"]
    status = run_git(root, "status", "--porcelain", check=False)
    return ["release_worktree_dirty"] if status.returncode or status.stdout.strip() else []


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
            selected = _immutable_tag_commit(
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
                )
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
