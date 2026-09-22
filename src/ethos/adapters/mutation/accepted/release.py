"""Select exact accepted release refs through the existing native Git transaction."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from filelock import FileLock
from filelock import Timeout

from ethos.adapters.mutation.proof import proof_for_repository_transition
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.commit.creation import create_signed_tag
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_object import zero_oid
from ethos.adapters.repo.git_ref_worktrees import sync_ref_worktrees
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.release import accepted_release_source
from ethos.adapters.repo.release import release_checkout_gaps
from ethos.adapters.repo.release import release_ref_subject
from ethos.adapters.repo.release import release_selection_command
from ethos.adapters.repo.release import release_tag_policy
from ethos.adapters.repo.release import require_release
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import canonical_json_digest

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation


@dataclass(frozen=True)
class _Selection:
    """One transient release request, not another lifecycle or policy carrier."""

    root: Path
    head: str
    previous: str
    tag: str
    branch: str
    identity_transition: bool = False

    @property
    def ref(self) -> str:
        return f"refs/heads/{self.branch}"

    def request(self) -> dict[str, str | bool]:
        return {
            "head": self.head,
            "previous": self.previous,
            "tag": self.tag,
            "release_ref": self.ref,
            **({"identity_transition": True} if self.identity_transition else {}),
        }

    @property
    def stored(self) -> Path:
        return (
            Path(git_common_dir(self.root))
            / "ethos/requests/release"
            / (canonical_json_digest(self.request()) + ".json")
        )

    @property
    def signing(self) -> Path:
        return self.stored.with_suffix(".signing")

    def command(self) -> str:
        return release_selection_command(
            self.root,
            head=self.head,
            previous=self.previous,
            tag=self.tag,
            apply=True,
            identity_transition=self.identity_transition,
        )

    def effect(
        self, accepted_ref: str, tag_oid: str = "", *, include_tag: bool = True
    ) -> GitEffect:
        """Assert aligned branches; reserve updates for actual state changes."""
        assertions = {accepted_ref: self.head}
        updates = {}
        if self.previous == self.head:
            assertions[self.ref] = self.head
        else:
            updates[self.ref] = GitRefUpdate(expected=self.previous, desired=self.head)
        if self.tag and include_tag:
            updates[f"refs/tags/{self.tag}"] = GitRefUpdate(
                expected=zero_oid(self.root), desired=tag_oid
            )
        return GitEffect(updates=updates, assertions=assertions)


def _release_paths(root: Path, branch: str) -> tuple[Path, ...]:
    raw = run_git(root, "worktree", "list", "--porcelain", "-z").stdout
    paths = []
    for block in raw.split("\0\0"):
        fields = dict(row.split(" ", 1) for row in block.split("\0") if " " in row)
        if fields.get("branch") == f"refs/heads/{branch}":
            paths.append(Path(fields["worktree"]))
    return tuple(paths)


def _observe(selection: _Selection, *, apply: bool, authorized: bool, plan: TransitionPlan | None):
    """Read fresh source, proof, permission and linked-worktree preconditions."""
    root, head = selection.root, selection.head
    policy = load_branch_role_policy(root)
    require_release(head and selection.previous, "release_exact_coordinates_required")
    if policy.release_mirror == "accepted_ff":
        require_release(
            selection.previous == head == ref_head(root, selection.ref),
            "release_mirror_requires_accepted_closeout",
        )
    require_release(not apply or authorized, "authorization_required")
    gaps = release_checkout_gaps(root, head) + hook_runtime_binding(root)["required_gaps"]
    require_release(not gaps, gaps[0] if gaps else "")
    accepted = accepted_release_source(root, head)
    proof, gaps = proof_for_repository_transition(
        root, head, attestation_id=str(plan.prior_attestations["proof"]["id"]) if plan else ""
    )
    require_release(proof is not None, gaps[0] if gaps else "release_source_not_proven")
    observed = ref_head(root, selection.ref)
    require_release(
        observed in {selection.previous, head} and is_ancestor(root, selection.previous, head),
        "release_ref_prestate_stale",
    )
    paths = _release_paths(root, selection.branch)
    gap = worktree_sync_gap(root, paths, selection.branch, observed, selection.previous, head)
    if gap and observed == head:
        gap = worktree_sync_gap(root, paths, selection.branch, head, head, head)
    require_release(not gap, "release_" + gap)
    version = release_tag_policy(root, head, selection.tag) if selection.tag else {}
    preview = None
    if not apply and (plan is not None or selection.previous != head):
        assert proof is not None
        preview = plan or _compile_plan(
            selection,
            selection.effect(f"refs/heads/{policy.accepted_branch}", include_tag=False),
            accepted,
            proof,
        )
        admit_git_effect(root, preview)
    return accepted, proof, observed, paths, version, preview


def _validate_request_plan(selection: _Selection, plan: TransitionPlan) -> None:
    """Re-derive complete permitted refs; a stored plan never grants broader effects."""
    effect = git_effect_from_plan(plan)
    require_release(
        plan.authority.get("actor")
        == (os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"),
        "release_request_actor_mismatch",
    )
    policy = load_branch_role_policy(selection.root)
    tag_oid = ""
    if selection.tag:
        tag_ref = f"refs/tags/{selection.tag}"
        update = effect.updates.get(tag_ref)
        require_release(update is not None, "release_request_tag_missing")
        assert update is not None
        require_release(update.expected == zero_oid(selection.root), "release_request_tag_invalid")
        release_ref_subject(selection.root, ref=tag_ref, old=update.expected, new=update.desired)
        tag_oid = update.desired
    require_release(
        effect == selection.effect(f"refs/heads/{policy.accepted_branch}", tag_oid)
        and plan.facts.get("head") == selection.head
        and plan.policy.get("transition") == "release.promote"
        and plan.policy.get("release_branch") == selection.branch
        and plan.facts.get("values", {}).get("release_request") == selection.request(),
        "release_request_binding_invalid",
    )


def _existing_plan(selection: _Selection) -> TransitionPlan | None:
    require_release(
        all(
            not path.is_symlink()
            for path in (selection.stored, selection.stored.parent, selection.stored.parent.parent)
        ),
        "release_request_unsafe",
    )
    if not selection.stored.exists():
        return None
    payload = json.loads(selection.stored.read_text())
    require_release(isinstance(payload, dict), "release_request_invalid")
    require_release(payload.get("request") == selection.request(), "release_request_collision")
    plan = TransitionPlan.model_validate(payload["plan"])
    _validate_request_plan(selection, plan)
    return plan


def _compile_plan(
    selection: _Selection, effect: GitEffect, accepted: dict[str, object], proof: Attestation
):
    return compile_observed_git_effect(
        selection.root,
        None,
        effect,
        head=selection.head,
        policy={
            "operation": "release.promote",
            "release_branch": selection.branch,
            "actor": os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos",
        },
        prior_attestations={
            "proof": proof.model_dump(mode="json"),
            "accepted_effect": accepted["accepted_effect"],
        },
        values={"release_request": selection.request(), "root": selection.root.as_posix()},
        identity_transition=selection.identity_transition,
    )


def _prepare_plan(selection: _Selection, accepted: dict[str, object], proof: Attestation):
    """Prepare exact native objects, then persist their single existing plan carrier."""
    root = selection.root
    oid = ""
    if selection.tag:
        tag_ref = f"refs/tags/{selection.tag}"
        require_release(not ref_head(root, tag_ref), "release_tag_already_exists")
        oid = create_signed_tag(
            root, name=selection.tag, head=selection.head, staging=selection.signing
        )
        release_ref_subject(root, ref=tag_ref, old=zero_oid(root), new=oid)
    effect = selection.effect(str(accepted["accepted_ref"]), oid)
    plan = _compile_plan(selection, effect, accepted, proof)
    raw = (
        json.dumps(
            {"request": selection.request(), "plan": plan.model_dump(mode="json")},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    write_content_addressed(selection.stored, raw.encode(), collision="release_request_collision")
    return plan


def _execute(
    selection: _Selection,
    plan: TransitionPlan,
    paths: tuple[Path, ...],
    accepted: dict[str, object],
    proof: Attestation,
):
    """Revalidate before CAS and retain exact pending worktree synchronization."""
    _validate_request_plan(selection, plan)
    expected = _compile_plan(selection, git_effect_from_plan(plan), accepted, proof)
    require_release(plan.digest == expected.digest, "release_request_evidence_stale")
    if selection.signing.exists():
        require_release(not selection.signing.is_symlink(), "release_request_unsafe")
        shutil.rmtree(selection.signing)
    require_release(current_tracked_head(selection.root) == selection.head, "release_source_stale")
    attestation = execute_git_effect(
        selection.root,
        plan,
        issuer=os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos",
    )
    sync = sync_ref_worktrees(
        selection.root, paths, selection.branch, selection.head, selection.previous
    )
    require_release(
        sync["worktree_sync"] not in {"failed", "dirty"}, "release_worktree_sync_pending"
    )
    return {
        "attestation": attestation.model_dump(mode="json"),
        "worktree_sync": sync,
        "request": str(selection.stored),
        "tag_oid": ref_head(selection.root, f"refs/tags/{selection.tag}") if selection.tag else "",
    }


def promote_release(
    root: Path,
    *,
    head: str,
    previous: str,
    tag: str = "",
    apply: bool = False,
    authorized: bool = False,
    identity_transition: bool = False,
) -> dict[str, object]:
    """Select an independent release or tag already aligned accepted-mirror content."""
    selection = _Selection(
        root,
        head,
        previous,
        tag,
        load_branch_role_policy(root).release_branch,
        identity_transition=identity_transition,
    )
    data: dict[str, object] = {"source": head, "previous": previous, "tag": tag}
    try:
        plan = _existing_plan(selection)
        accepted, proof, observed, paths, version, preview = _observe(
            selection, apply=apply, authorized=authorized, plan=plan
        )
        data.update(
            accepted=accepted, version=version, release_ref=selection.ref, observed=observed
        )
        if preview is not None:
            data.update(
                transition_plan=preview.model_dump(mode="json"),
                preview_scope="branch-and-existing-effects" if plan else "branch-only",
            )
        require_release(
            plan is not None or observed != head or previous == head,
            "release_effect_evidence_missing",
        )
        require_release(
            plan is not None or not tag or not ref_head(root, f"refs/tags/{tag}"),
            "release_tag_already_exists",
        )
        if apply and (tag or previous != head):
            assert proof is not None
            lock = selection.stored.parent / ".lock"
            lock.parent.mkdir(parents=True, exist_ok=True)
            with FileLock(lock, timeout=0, mode=0o600, preserve_lock_file=True):
                plan = _existing_plan(selection)
                accepted, proof, _, paths, _, _ = _observe(
                    selection, apply=True, authorized=True, plan=plan
                )
                assert proof is not None
                plan = plan or _prepare_plan(selection, accepted, proof)
                data.update(_execute(selection, plan, paths, accepted, proof))
    except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError, Timeout) as error:
        data["request"] = str(selection.stored) if selection.stored.exists() else ""
        if isinstance(error, ProcessExecutionError):
            data["process_failure"] = error.evidence()
        unknown = (
            isinstance(error, (OSError, subprocess.SubprocessError))
            or (
                isinstance(error, ProcessExecutionError)
                and error.observation.get("outcome") != "unchanged"
            )
            or str(error).startswith("git_effect_partial_effect_")
            or str(error)
            in {
                "release_tag_signing_outcome_unknown",
                "release_worktree_sync_pending",
            }
        )
        waiting = isinstance(error, Timeout)
        action = (
            selection.command()
            if unknown or waiting
            else f"ethos status --root {shlex.quote(str(root))} --json"
        )
        if str(error) == "release_mirror_requires_accepted_closeout":
            action = f"ethos land --closeout --root {shlex.quote(str(root))} --json"
        if str(error) == "release_tag_signing_outcome_unknown":
            action = shlex.join(
                (
                    "git",
                    "--git-dir",
                    str(selection.signing),
                    "fsck",
                    "--no-reflogs",
                    "--unreachable",
                )
            )
        return {
            "verdict": "unknown" if unknown and not waiting else "block",
            "state": "waiting" if waiting else "partial_transition" if unknown else "blocked",
            "required_gaps": ["release_in_progress" if waiting else str(error)],
            "next_action": action,
            "data": data,
        }
    return {
        "verdict": "pass",
        "state": "released" if apply else "ready_to_release",
        "required_gaps": [],
        "next_action": "" if apply else selection.command(),
        "data": data,
    }
