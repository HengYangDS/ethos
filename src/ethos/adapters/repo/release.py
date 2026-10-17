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
from ethos.adapters.repo.git import git_stdout
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
from ethos.repository.release.configuration import release_config_from_text
from ethos.repository.release.identity import product_version_from_text
from ethos.repository.release.publication import publication_proof_selection
from ethos.repository.release.publication import publication_ref_role

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.branch.roles import BranchRolePolicy


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
        return product_version_from_text(raw)
    payload = json.loads(raw) if name.endswith(".json") else tomllib.loads(raw)
    require_release(isinstance(payload, dict), "release_version_source_not_object")
    source = payload if name.endswith(".json") else payload.get("project", {})
    require_release(isinstance(source, dict), "release_version_source_not_object")
    if "version" not in source:
        return ""
    require_release("version" not in source.get("dynamic", ()), "release_version_source_dynamic")
    value = source["version"]
    require_release(isinstance(value, str), "release_version_source_not_text")
    return product_version_from_text(value + "\n")


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
    return version


def release_publication_head(root: Path, *, ref: str = "", new: str = "") -> str:
    """Return the accepted commit that publishing one ref object delivers.

    Branches and new release tags deliver the current accepted head. An existing
    tag object delivers the earlier accepted commit at which its attested release
    effect created it, so a peer that missed that release can still receive it.
    """
    policy = load_branch_role_policy(root)
    accepted_ref = f"refs/heads/{policy.accepted_branch}"
    head = ref_head(root, accepted_ref)
    if not ref.startswith("refs/tags/") or not new:
        return head
    released = git_stdout(root, "rev-parse", "--verify", "--quiet", f"{new}^{{commit}}")
    if not released or released == head or not is_ancestor(root, released, head):
        return head
    plan = recover_plan(
        root,
        operation="release.promote",
        desired=new,
        ref_name=ref,
        current_postconditions=False,
    )
    if plan is None:
        return head
    effect = git_effect_from_plan(plan)
    update = effect.updates.get(ref)
    attested = (
        update is not None
        and (update.expected, update.desired) == (zero_oid(root), new)
        and effect.assertions.get(accepted_ref) == released
    )
    return released if attested else head


def publication_proof_head(root: Path, refs: tuple[str, ...], head: str) -> str:
    """Prove a tag's release commit; every other publication proves the checkout head."""
    if not refs or not all(ref.startswith("refs/tags/") for ref in refs):
        return head
    tag = ref_head(root, refs[0])
    try:
        maintenance = release_provenance(root, ref=refs[0], oid=tag) if tag else None
        if maintenance is not None:
            return str(maintenance.facts["head"])
        return release_publication_head(root, ref=refs[0], new=tag) if tag else head
    except ValueError:
        return head


def accepted_release_source(
    root: Path, head: str, *, base: str = "", ref: str = "", new: str = ""
) -> dict[str, object]:
    """Validate exact accepted content without claiming historical signatures."""
    require_release(
        bool(base) or release_publication_head(root, ref=ref, new=new) == head,
        "release_source_not_current_accepted",
    )
    return _accepted_release_content(root, head, base=base)


def _accepted_release_content(root: Path, head: str, *, base: str) -> dict[str, object]:
    """Validate selected content; source selection belongs to the caller's fresh observation."""
    policy = release_branch_policy(root)
    accepted_ref = f"refs/heads/{policy.accepted_branch}"
    current = ref_head(root, accepted_ref)
    if base:
        require_release(
            ref_head(root, base) == base and is_ancestor(root, base, head),
            "release_base_not_exact_ancestor",
        )
        require_release(
            not observe_git_object(root, base, "commit")["required_gaps"],
            "release_base_signature_untrusted",
        )
        gaps = list(
            cast(
                "list[str]",
                commit_policy_report(
                    root, commit_policy_for_revision(root, current), base, verify_trust=False
                )["required_gaps"],
            )
        )
        gaps += validate_replayed_commits(
            root,
            baseline_commit=base,
            proposed_commit=head,
            policy=commit_policy_for_revision(root, current),
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
    return {
        "accepted_ref": accepted_ref,
        "head": head,
        **({"base": base} if base else {}),
        "accepted_effect": closeout.attestation.model_dump(mode="json"),
        "accepted_plan": closeout.plan.digest,
        "provenance": closeout.projection(),
        "source": source,
    }


def accepted_delivery_report(
    root: Path, *, head: str, proposed: str, target: str, remote_head: str, remote: str
) -> dict[str, object]:
    """Describe accepted-content reuse without pretending the remote is accepted.

    No contribution range is introduced at this boundary. Current source trust,
    accepted effect and policy remain independently checked.
    """
    try:
        accepted = accepted_release_source(root, head, ref=target, new=proposed)
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
    root: Path,
    *,
    ref: str,
    old: str,
    new: str,
    allow_identical: bool = False,
    base: str = "",
    publication: bool = False,
) -> str:
    """Require native release identity; callers separately admit proof and intent.

    Creation selects the current accepted head. Publishing an existing tag object
    may instead deliver the accepted commit of its attested release.
    """
    policy = release_branch_policy(root)
    accepted_head = ref_head(root, policy.accepted_branch)
    head = accepted_head
    published = {"ref": ref, "new": new} if publication else {}
    if ref.startswith("refs/tags/"):
        selected = _immutable_tag_commit(
            root, ref=ref, old=old, new=new, allow_identical=allow_identical or publication
        )
        head = release_publication_head(root, **published)
        if selected != head:
            plan = release_provenance(root, ref=ref, oid=new)
            base = base or (str(plan.facts["values"]["release_request"]["base"]) if plan else "")
            base = base or lane_creation_boundary(root, selected)
            require_release(base, "release_tag_source_untrusted")
        head = selected
        release_tag_policy(root, head, ref.removeprefix("refs/tags/"))
    else:
        require_release(new == head, "release_source_not_current_accepted")
        require_release(
            old == zero_oid(root) or is_ancestor(root, old, new), "release_not_fast_forward"
        )
    _accepted_release_content(root, head, base=base)
    require_release(
        ref_head(root, policy.accepted_branch) == accepted_head,
        "release_source_not_current_accepted",
    )
    return head


def release_provenance(root: Path, *, ref: str, oid: str):
    """Read the original completed tag-only effect, never a new acceptance registry."""
    plan = recover_plan(
        root,
        operation="release.promote",
        desired=oid,
        ref_name=ref,
        current_postconditions=False,
    )
    if plan is None or not plan.facts.get("values", {}).get("release_request", {}).get("base"):
        return None
    effect = git_effect_from_plan(plan)
    require_release(
        set(effect.updates) == {ref} and effect.updates[ref].expected == zero_oid(root),
        "release_maintenance_effect_invalid",
    )
    return plan


def maintenance_publication_baseline(root: Path, *, ref: str, oid: str, head: str, initial: bool):
    """Derive publication provenance from the single completed maintenance effect."""
    plan = release_provenance(root, ref=ref, oid=oid) if ref.startswith("refs/tags/") else None
    if plan is None:
        return None
    require_release(plan.facts.get("head") == head, "release_maintenance_source_mismatch")
    base = str(plan.facts["values"]["release_request"]["base"])
    accepted = accepted_release_source(root, head, base=base)
    require_release(
        mutable_json(plan.prior_attestations["accepted_effect"]) == accepted["accepted_effect"],
        "release_maintenance_accepted_evidence_changed",
    )
    return (
        {
            "plan_digest": plan.digest,
            "operation": "release.promote",
            "base": base,
            "candidate_head": head,
            "proof_attestation_id": str(plan.prior_attestations["proof"]["id"]),
            "provenance": accepted["provenance"],
        },
        [],
        base if initial else "",
        "accepted_effect" if initial else "",
    )


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


def tag_publication_gaps(root: Path, ref: str, old: str, new: str, *, role: str) -> list[str]:
    """Check the complete tag object at the native pre-push boundary."""
    if not ref.startswith("refs/tags/"):
        return []
    try:
        if publication_proof_selection(role) == "review_object":
            _immutable_tag_commit(root, ref=ref, old=old, new=new, allow_identical=True)
        else:
            release_ref_subject(root, ref=ref, old=old, new=new, publication=True)
    except (OSError, ValueError) as error:
        return [str(error)]
    return []


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
) -> tuple[dict[str, object], list[str], str, str]:
    """Resolve one accepted or maintenance source for exact protected publication."""
    release = role in {"release_root", "release_publication"}
    initial = remote_head in {"0" * 40, "0" * 64}
    try:
        maintenance = (
            maintenance_publication_baseline(
                repo, ref=target_ref, oid=source_oid, head=proof_head, initial=initial
            )
            if release
            else None
        )
        if maintenance is not None:
            return maintenance
        required = (
            branch == policy.accepted_branch
            or release
            or (initial and publication_proof_selection(role) == "repository_transition")
        )
        if not required:
            return {}, [], "", ""
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
        )
    except ValueError as error:
        return {}, [str(error)], "", ""
