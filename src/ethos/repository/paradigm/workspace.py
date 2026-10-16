"""Workspace binding conformance: the commit policy is the only workspace table.

The paradigm fixes every branch role, the commit grammar and the SSH signature, and
the release binding declares the release mirror, so a `[branch_roles]` table, like
any other workspace table, and a restated grammar or signing field are declarations
no reader consults. Each gap names the declaration and its removal; an accepted
fast-forward mirror instead names its move to the release binding.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import RELEASE_MIRROR_FIELD
from ethos.contracts.branch.roles import RETIRED_BRANCH_ROLE_FIELDS
from ethos.contracts.branch.roles import SIBLING_WORKTREE_FIELD
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text
from ethos.repository.policy.commit import RETIRED_COMMIT_POLICY_FIELDS

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm

_ROLES = "branch_roles"


def workspace_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Report every workspace table but the commit policy, and its restated grammar or signature."""
    workspace = f"{paradigm.binding.root}/workspace.toml"
    declared = _declared(root, workspace, tracked)
    if declared is None:
        return  # The workspace policy owners report an unreadable binding.
    # A role table that is not a table is the legacy role-name reader's gap.
    for key, value in declared.items():
        if key in paradigm.binding.workspace_tables:
            continue
        if key == _ROLES and isinstance(value, dict) and value:
            yield from _role_gaps(paradigm, root, tracked, workspace, value)
        elif key != _ROLES or isinstance(value, dict):
            yield ParadigmGap("workspace-binding", f"{workspace}:{key}", _table_repair(key))
    policy = declared.get("commit_policy", {})
    if not isinstance(policy, dict):
        return  # The commit policy owner reports a table that is not a table.
    if "subject_pattern" in policy:
        yield ParadigmGap(
            "commit-grammar",
            f"{workspace}:commit_policy.subject_pattern",
            "remove subject_pattern; the repository paradigm owns the commit grammar, "
            "and scopes = [...] restricts its scopes",
        )
    for field in (field for field in RETIRED_COMMIT_POLICY_FIELDS if field in policy):
        yield ParadigmGap(
            "commit-signature",
            f"{workspace}:commit_policy.{field}",
            f"remove {field}; the repository paradigm requires an SSH signature on every commit",
        )


def _role_gaps(
    paradigm: RepositoryParadigm,
    root: Path,
    tracked: frozenset[str],
    workspace: str,
    roles: dict[str, object],
) -> Iterator[ParadigmGap]:
    """Name each retired role field; an undeclared accepted mirror also names its new carrier."""
    release = f"{paradigm.binding.root}/release.toml"
    declared_release = (_declared(root, release, tracked) or {}).get("release")
    mirror_declared = isinstance(declared_release, dict) and "mirror" in declared_release
    for field in (field for field in RETIRED_BRANCH_ROLE_FIELDS if field in roles):
        moved = field == RELEASE_MIRROR_FIELD and roles[field] == RELEASE_MIRROR_ACCEPTED_FF
        repair = (
            f"remove {field}; {release} declares the release mirror"
            if field == RELEASE_MIRROR_FIELD and mirror_declared
            else _field_repair(field, roles[field], release)
        )
        yield ParadigmGap("branch-roles", f"{workspace}:{_ROLES}.{field}", repair)
        if moved and not mirror_declared:
            yield ParadigmGap(
                "release-mirror",
                f"{release}:release.mirror",
                f'declare [release] mirror = "{RELEASE_MIRROR_ACCEPTED_FF}", which '
                f"{workspace} still declares as {_ROLES}.{RELEASE_MIRROR_FIELD}",
            )


def _field_repair(field: str, value: object, release: str) -> str:
    """Name the removal of one retired branch-role field and what replaces it."""
    if field == SIBLING_WORKTREE_FIELD:
        return f"remove {field}; the repository paradigm places Work Lanes in sibling worktrees"
    if field == RELEASE_MIRROR_FIELD:
        if value == RELEASE_MIRROR_ACCEPTED_FF:
            return f'move {field} to {release} as [release] mirror = "{value}"'
        return (
            f"remove {field}; the release mirror is independent unless {release} "
            "declares [release] mirror"
        )
    name = getattr(BranchRolePolicy(), field)
    rename = "" if value == name else " after closeout renames the ref"
    return f"remove {field}{rename}; the repository paradigm fixes it as {name}"


def _table_repair(key: str) -> str:
    """Name the removal of a workspace table that no reader consults."""
    if key == _ROLES:
        return f"remove {key}; the repository paradigm fixes every branch role"
    return f"remove {key}; no ETHOS reader consults it"


def _declared(root: Path, path: str, tracked: frozenset[str]) -> dict[str, object] | None:
    """Parse one tracked binding; an absent one declares nothing and an unreadable one is None."""
    source = tracked_text(root, path, tracked)
    try:
        return tomllib.loads(source) if source is not None else {}
    except tomllib.TOMLDecodeError:
        return None
