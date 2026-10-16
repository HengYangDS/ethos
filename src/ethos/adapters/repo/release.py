"""Observe exact accepted release subjects and their native version materials."""

from __future__ import annotations

import json
import shlex
import tomllib
from typing import TYPE_CHECKING

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.commit.admission import commit_policy_for_revision
from ethos.adapters.repo.commit.provenance import accepted_provenance
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import declares_transition
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import validate
from ethos.adapters.repo.git_object import observe_git_object
from ethos.adapters.repo.git_object import zero_oid
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import git_effect_from_plan
from ethos.repository.release.changelog import changelog_errors
from ethos.repository.release.changelog import semver_from_text
from ethos.repository.release.configuration import release_config_from_text
from ethos.repository.release.publication import publication_ref_role

if TYPE_CHECKING:
    from pathlib import Path


def require_release(condition: object, gap: str) -> None:
    """Require one precise release invariant without converting unknown into success."""
    if not condition:
        raise ValueError(gap)


def release_selection_command(
    root: Path,
    *,
    head: str,
    previous: str,
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


def declared_release_tag(root: Path, head: str, ref: str) -> bool:
    """Select only the release tags declared by current committed policy."""
    policy = load_branch_role_policy(root)
    declaration = release_config_from_text(committed_file_text(root, head, ".ethos/release.toml"))
    tags = tuple(declaration.get("protected_refs", {}).get("tags", ()))
    return bool(publication_ref_role(policy, ref, tags)[2])


def release_tag_policy(root: Path, head: str, name: str) -> dict[str, str]:
    """Bind a requested tag to exact committed declaration and native version."""
    require_release(
        declared_release_tag(root, head, f"refs/tags/{name}"), "release_tag_not_declared"
    )
    version = committed_release_version(root, head)
    require_release(name == f"v{version['version']}", "release_tag_version_mismatch")
    if errors := changelog_errors(
        committed_file_text(root, head, "CHANGELOG.md"), target=version["version"]
    ):
        raise ValueError(errors[0])
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
    attested = _attested_release(root, ref=ref, tag=new, accepted_ref=accepted_ref, commit=released)
    return released if attested else head


def publication_proof_head(root: Path, refs: tuple[str, ...], head: str) -> str:
    """Prove a tag's release commit; every other publication proves the checkout head."""
    if not refs or not all(ref.startswith("refs/tags/") for ref in refs):
        return head
    tag = ref_head(root, refs[0])
    try:
        return release_publication_head(root, ref=refs[0], new=tag) if tag else head
    except ValueError:
        return head


def _attested_release(root: Path, *, ref: str, tag: str, accepted_ref: str, commit: str) -> bool:
    """Select only a validated release effect that created this exact tag at commit."""
    zero = zero_oid(root)
    for attestation in read_attestation_set(root)[1]:
        if attestation.predicate != "effect:git-ref-update" or not declares_transition(
            attestation, "release.promote"
        ):
            continue
        try:
            plan = plan_from_attestation(attestation)
            effect = git_effect_from_plan(plan)
            update = effect.updates.get(ref)
            if (
                update is None
                or (update.expected, update.desired) != (zero, tag)
                or effect.assertions.get(accepted_ref) != commit
            ):
                continue
            validate(
                root,
                effect,
                attestation,
                issuer=attestation.verifier,
                plan=plan,
                current_postconditions=False,
            )
        except ValueError:
            continue
        return True
    return False


def accepted_release_source(
    root: Path, head: str, *, ref: str = "", new: str = ""
) -> dict[str, object]:
    """Validate exact accepted content without claiming historical signatures."""
    policy = load_branch_role_policy(root)
    accepted_ref = f"refs/heads/{policy.accepted_branch}"
    require_release(
        release_publication_head(root, ref=ref, new=new) == head,
        "release_source_not_current_accepted",
    )
    source = observe_git_object(root, head, "commit")
    require_release(not source["required_gaps"], "release_source_signature_untrusted")
    closeout = accepted_provenance(
        root,
        accepted_ref=accepted_ref,
        candidate_ref=f"refs/heads/{policy.candidate_branch}",
        head=head,
    )
    require_release(closeout is not None, "accepted_closeout_effect_not_attested")
    assert closeout is not None
    return {
        "accepted_ref": accepted_ref,
        "head": head,
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
    root: Path, *, ref: str, old: str, new: str, publication: bool = False
) -> str:
    """Require native release identity; callers separately admit proof and intent.

    Creation selects the current accepted head. Publishing an existing tag object
    may instead deliver the accepted commit of its attested release.
    """
    policy = load_branch_role_policy(root)
    head = ref_head(root, policy.accepted_branch)
    published = {"ref": ref, "new": new} if publication else {}
    if ref.startswith("refs/tags/"):
        head = release_publication_head(root, **published)
        source = observe_git_object(root, new, "annotated-tag")
        require_release(
            not source["required_gaps"] and source["peeled_commit"] == head,
            "release_tag_source_untrusted",
        )
        # Newly prepared objects have no source ref yet; inspect the native tag header.
        header = run_git(root, "cat-file", "tag", new).stdout.partition("\n\n")[0]
        names = [
            line.removeprefix("tag ") for line in header.splitlines() if line.startswith("tag ")
        ]
        require_release(names == [ref.removeprefix("refs/tags/")], "release_tag_name_mismatch")
        release_tag_policy(root, head, ref.removeprefix("refs/tags/"))
        require_release(
            old == zero_oid(root) or (publication and old == new), "release_tag_immutable"
        )
    else:
        require_release(new == head, "release_source_not_current_accepted")
        require_release(
            old == zero_oid(root) or is_ancestor(root, old, new), "release_not_fast_forward"
        )
    accepted_release_source(root, head, **published)
    return head


def release_tag_publication_gaps(root: Path, ref: str, old: str, new: str) -> list[str]:
    """Check the complete tag object at the native pre-push boundary."""
    if not ref.startswith("refs/tags/"):
        return []
    try:
        release_ref_subject(root, ref=ref, old=old, new=new, publication=True)
    except (OSError, ValueError) as error:
        return [str(error)]
    return []


def release_checkout_gaps(root: Path, head: str) -> list[str]:
    """Require the exact clean accepted checkout before local release effects."""
    policy = load_branch_role_policy(root)
    if current_branch(root) != policy.accepted_branch or current_tracked_head(root) != head:
        return ["release_accepted_root_required"]
    status = run_git(root, "status", "--porcelain", check=False)
    return ["release_worktree_dirty"] if status.returncode or status.stdout.strip() else []
