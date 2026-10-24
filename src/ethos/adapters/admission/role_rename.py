"""Git admission for renaming legacy role refs to the names the paradigm fixes.

A repository adopted under a table that named other role refs keeps those refs
protected after the paradigm fixed the names. Only accepted closeout's rename
moves them: one ref transaction deletes each legacy role ref and creates the
standard role ref at the same head, so no content changes. Admission re-derives
that shape from the committed tables and the live refs before it admits any line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.admission.ref_intent import plan_ref_intents
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import ref_head
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import declared_role_names
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from pathlib import Path

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
    """Map committed legacy roles and retained topics to unchanged standard destinations."""
    text = committed_file_text(root, head, ".ethos/workspace.toml")
    names = legacy_role_names(text)
    standard = BranchRolePolicy()
    renames = {
        f"refs/heads/{legacy}": (f"refs/heads/{getattr(standard, role)}", value)
        for role, legacy in names.items()
        if (value := ref_head(root, f"refs/heads/{legacy}"))
    }
    for field in ("work_branch_prefix", "proposal_branch_prefix"):
        prefix = declared_role_names(text).get(field, "")
        if not prefix or prefix == getattr(standard, field):
            continue
        for line in git_stdout(
            root, "for-each-ref", "--format=%(refname) %(objectname)", f"refs/heads/{prefix}"
        ).splitlines():
            ref, value = line.split(" ", 1)
            legacy = f"refs/heads/{prefix}"
            target = f"refs/heads/{getattr(standard, field)}{ref.removeprefix(legacy)}"
            if ref.startswith(legacy):
                renames[ref] = (target, value)
    return renames


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
        "decision": {"action": "block" if gaps else "allow", "reason": reason or gaps[0]},
        "required_gaps": gaps,
        "next_action": "ethos land --closeout" if gaps else "",
    }
