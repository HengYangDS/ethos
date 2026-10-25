"""Admit declared legacy branch identity renames without changing their content.

Protected role renames and one live holder's retained Work Lane share the same
exact create/delete transaction. Admission re-derives the relation from committed
role declarations, current refs and, for a topic, fresh linked-worktree coordination.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.admission.ref_intent import plan_ref_intents
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import declared_role_names
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from ethos.adapters.store.state.lease.projection import LeaseRow

ROLE_RENAME_OPERATION = "branch-roles.rename"
RENAMED_ROLES = ("release_branch", "accepted_branch", "candidate_branch")
_ZERO_OIDS = {"0" * 40, "0" * 64}


def legacy_role_names(text: str) -> dict[str, str]:
    """Map each renamed role that a workspace table declares under a legacy name to that name."""
    declared, standard = declared_role_names(text), BranchRolePolicy()
    return {
        role: name
        for role in RENAMED_ROLES
        if (name := declared.get(role, "")) and name != getattr(standard, role)
    }


def legacy_proposal_prefix(text: str) -> str:
    """Return the proposal prefix a workspace table declares under a legacy name, or ''."""
    prefix = declared_role_names(text).get("proposal_branch_prefix", "")
    return prefix if prefix != BranchRolePolicy().proposal_branch_prefix else ""


def legacy_role_renames(root: Path, head: str) -> dict[str, tuple[str, str]]:
    """Map each legacy role ref the committed table at head declares to its standard ref."""
    names = legacy_role_names(committed_file_text(root, head, ".ethos/workspace.toml"))
    standard = BranchRolePolicy()
    return {
        f"refs/heads/{legacy}": (f"refs/heads/{getattr(standard, role)}", value)
        for role, legacy in names.items()
        if (value := ref_head(root, f"refs/heads/{legacy}"))
    }


def retained_topic_target(root: Path, branch: str, head: str) -> str:
    """Derive one retained Work Lane's fixed name from its committed declaration."""
    declared = declared_role_names(committed_file_text(root, head, ".ethos/workspace.toml"))
    standard = BranchRolePolicy()
    prefix = declared.get("work_branch_prefix", "")
    if (
        not prefix.endswith("/")
        or prefix == standard.work_branch_prefix
        or not branch.startswith(prefix)
        or not (suffix := branch.removeprefix(prefix))
        or not standard.is_topic_branch(branch)
        or branch in {declared.get(role) for role in RENAMED_ROLES}
    ):
        return ""
    target = standard.work_branch(suffix)
    if run_git(root, "check-ref-format", f"refs/heads/{target}", check=False).returncode:
        msg = "retained_topic_target_invalid"
        raise ValueError(msg)
    return target


def require_owned_topic(
    root: Path, source: str, target: str, *, recovering: bool = False
) -> LeaseRow:
    """Admit the selected linked Work Lane and its live holder, never a foreign binding."""
    bound = git_stdout(root, "symbolic-ref", "--quiet", "HEAD")
    allowed = {f"refs/heads/{source}"}
    if recovering:
        allowed.add(f"refs/heads/{target}")
    linked = [
        fields
        for block in git_stdout(root, "worktree", "list", "--porcelain").split("\n\n")
        if (fields := dict(line.partition(" ")[::2] for line in block.splitlines())).get("branch")
        in allowed
    ]
    if (
        bound not in allowed
        or len(linked) != 1
        or Path(linked[0].get("worktree", "")).resolve() != root.resolve()
        or (root / ".git").resolve() == Path(git_common_dir(root)).resolve()
    ):
        msg = "retained_topic_worktree_binding_mismatch"
        raise ValueError(msg)
    db = state_database(root)
    lease = observe_lease(db, source)
    if lease.state != "valid" or lease.row is None:
        msg = f"retained_topic_lease_{lease.state}:{source}"
        raise ValueError(msg)
    if lease.row.holder_ref != os.environ.get("ETHOS_ACTOR", "").strip():
        msg = "lease_actor_mismatch"
        raise ValueError(msg)
    if observe_lease(db, target).state != "missing":
        msg = f"retained_topic_target_lease_present:{target}"
        raise ValueError(msg)
    return lease.row


def role_rename_ref_report(
    repo: Path, ref_name: str, old_value: str, new_value: str
) -> dict[str, object] | None:
    """Admit one line of a legacy role rename, refuse a legacy role ref move, else return None."""
    update = GitRefUpdate(expected=old_value, desired=new_value)
    intents = plan_ref_intents(
        repo, ref_name=ref_name, update=update, operation=ROLE_RENAME_OPERATION
    )
    if intents:
        gaps = _rename_shape_gaps(repo, intents)
        if not gaps:
            claimed = claim_ref_intent(
                root=repo,
                ref_name=ref_name,
                update=update,
                operation=ROLE_RENAME_OPERATION,
                phase="prepared",
            )
            gaps = [str(claimed["gap"])] if claimed["gap"] else []
        return _report(ref_name, old_value, new_value, gaps, "legacy_role_rename")
    if old_value in _ZERO_OIDS or ref_name not in _legacy_refs(repo, old_value):
        return None
    return _report(ref_name, old_value, new_value, ["legacy_role_ref_protected"], "")


def _rename_shape_gaps(repo: Path, intents: tuple[tuple[str, str, str], ...]) -> list[str]:
    """Require exact legacy-to-standard renames of the live refs at unchanged heads."""
    deleted = {ref: old for ref, old, new in intents if new in _ZERO_OIDS}
    created = {ref: new for ref, old, new in intents if old in _ZERO_OIDS}
    try:
        expected = {
            legacy: target
            for value in set(deleted.values())
            for legacy, target in legacy_role_renames(repo, value).items()
            if deleted.get(legacy) == target[1]
        }
        topics = {
            source: (f"refs/heads/{target}", head)
            for source, head in deleted.items()
            if source not in expected
            and (target := retained_topic_target(repo, source.removeprefix("refs/heads/"), head))
        }
        if topics:
            if len(topics) != 1 or expected:
                return ["legacy_role_rename_shape_invalid"]
            source, (target, _head) = next(iter(topics.items()))
            require_owned_topic(
                repo,
                source.removeprefix("refs/heads/"),
                target.removeprefix("refs/heads/"),
            )
            expected = topics
    except (TypeError, ValueError):
        return ["legacy_role_rename_policy_unavailable"]
    if (
        not expected
        or len(intents) != len(deleted) + len(created)
        or set(deleted) != set(expected)
        or created != dict(expected.values())
        or any(ref_head(repo, ref) for ref in created)
    ):
        return ["legacy_role_rename_shape_invalid"]
    return []


def _legacy_refs(repo: Path, head: str) -> set[str]:
    """Return the legacy role refs that the committed table at head still declares."""
    try:
        return set(legacy_role_renames(repo, head))
    except (TypeError, ValueError):
        return set()


def _report(
    ref_name: str, old_value: str, new_value: str, gaps: list[str], reason: str
) -> dict[str, object]:
    return {
        "verdict": "block" if gaps else "pass",
        "state": "blocked" if gaps else "admitted",
        "hook": "reference-transaction",
        "ref": ref_name,
        "branch": ref_name.removeprefix("refs/heads/"),
        "old_value": old_value,
        "new_value": new_value,
        "decision": {
            "action": "block" if gaps else "allow",
            "reason": reason or gaps[0],
        },
        "required_gaps": gaps,
        "next_action": "ethos land --closeout" if gaps else "",
    }
