"""Define strict branch roles and their repository policy interpretation.

The repository paradigm fixes every role name: release `main`, accepted `dev`,
candidate `candidate/dev`, Work Lanes under `work/` and proposals under
`proposal/`. A `[branch_roles]` table declares only the release mirror and the
canonical sibling worktrees; a name it still declares is a legacy declaration that
the readers ignore and that accepted closeout renames to the paradigm's name.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from pathlib import Path

ROLE_RELEASE_ROOT = "release_root"
ROLE_ACCEPTED_ROOT = "accepted_root"
ROLE_CANDIDATE = "candidate"
ROLE_WORK_LANE = "work_lane"
ROLE_DETACHED = "detached"
ROLE_OTHER = "other"

RELEASE_MIRROR_ACCEPTED_FF = "accepted_ff"
_STRICT_BRANCH_ROLE_TABLE_ERROR = "branch_roles must be a table"
_STRICT_BRANCH_ROLE_TEXT_ERROR = "branch_roles text fields must be canonical strings"
_STRICT_BRANCH_ROLE_MIRROR_ERROR = "branch_roles release_mirror is invalid"
_STRICT_BRANCH_ROLE_SIBLING_ERROR = "branch_roles canonical_sibling_worktrees must be boolean"
_UNKNOWN_BRANCH_ROLE_FIELDS_ERROR = "branch_roles contains unknown fields"
ROLE_NAME_FIELDS = (
    "release_branch",
    "accepted_branch",
    "candidate_branch",
    "work_branch_prefix",
    "proposal_branch_prefix",
)
_BRANCH_ROLE_FIELDS = {*ROLE_NAME_FIELDS, "release_mirror", "canonical_sibling_worktrees"}
PROTECTED_WRITE_ROLES = frozenset(
    {
        ROLE_RELEASE_ROOT,
        ROLE_ACCEPTED_ROOT,
        ROLE_CANDIDATE,
        ROLE_DETACHED,
        ROLE_OTHER,
    }
)


@dataclass(frozen=True, slots=True)
class BranchRolePolicy:
    release_branch: str = "main"
    accepted_branch: str = "dev"
    candidate_branch: str = "candidate/dev"
    work_branch_prefix: str = "work/"
    proposal_branch_prefix: str = "proposal/"
    release_mirror: str = "independent"
    canonical_sibling_worktrees: bool = False

    def role_for_branch(self, branch: str) -> str:
        exact_roles = (
            (ROLE_DETACHED, ROLE_DETACHED),
            (self.release_branch, ROLE_RELEASE_ROOT),
            (self.accepted_branch, ROLE_ACCEPTED_ROOT),
            (self.candidate_branch, ROLE_CANDIDATE),
        )
        for branch_name, role in exact_roles:
            if branch == branch_name:
                return role
        return (
            ROLE_WORK_LANE
            if self.work_branch_prefix and branch.startswith(self.work_branch_prefix)
            else ROLE_OTHER
        )

    def work_branch(self, slug: str) -> str:
        return f"{self.work_branch_prefix}{slug}"

    def is_topic_branch(self, branch: str) -> bool:
        """Identify a named local topic independently of authoring permission."""
        return bool(branch) and self.role_for_branch(branch) in {ROLE_WORK_LANE, ROLE_OTHER}

    def proposal_branch_for_source(self, branch: str) -> str:
        if not self.work_branch_prefix or not branch.startswith(self.work_branch_prefix):
            return ""
        return f"{self.proposal_branch_prefix}{branch.removeprefix(self.work_branch_prefix)}"

    def candidate_effect(self, *, branch: str, current_head: str, candidate_head: str) -> GitEffect:
        """Compile the unique role-bound candidate CAS; publication is a different effect."""
        return GitEffect(
            updates={
                f"refs/heads/{self.candidate_branch}": GitRefUpdate(
                    expected=candidate_head, desired=current_head
                )
            },
            assertions={f"refs/heads/{branch}": current_head},
        )

    @property
    def protected_branches(self) -> tuple[str, ...]:
        branches = [self.release_branch, self.accepted_branch]
        return tuple(
            branch
            for index, branch in enumerate(branches)
            if branch and branch not in branches[:index]
        )

    def semantic_order(self) -> tuple[dict[str, str], ...]:
        return (
            {
                "role": ROLE_RELEASE_ROOT,
                "kind": "exact_branch",
                "config_key": "release_branch",
                "pattern": self.release_branch,
            },
            {
                "role": ROLE_ACCEPTED_ROOT,
                "kind": "exact_branch",
                "config_key": "accepted_branch",
                "pattern": self.accepted_branch,
            },
            {
                "role": ROLE_CANDIDATE,
                "kind": "exact_branch",
                "config_key": "candidate_branch",
                "pattern": self.candidate_branch,
            },
            {
                "role": ROLE_WORK_LANE,
                "kind": "branch_prefix",
                "config_key": "work_branch_prefix",
                "pattern": f"{self.work_branch_prefix}*",
            },
        )

    def as_status_policy(self) -> dict[str, object]:
        return {
            "release_branch": self.release_branch,
            "accepted_branch": self.accepted_branch,
            "candidate_branch": self.candidate_branch,
            "work_branch_prefix": self.work_branch_prefix,
            "proposal_branch_prefix": self.proposal_branch_prefix,
            "release_mirror": self.release_mirror,
            "semantic_order": [dict(record) for record in self.semantic_order()],
        }


def branch_role_policy_from_text(text: str) -> BranchRolePolicy:
    """Parse branch-role policy text without filesystem or provider access."""
    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return BranchRolePolicy()
    raw_policy = payload.get("branch_roles")
    if not isinstance(raw_policy, dict):
        return BranchRolePolicy()
    if set(raw_policy) - (_BRANCH_ROLE_FIELDS | {"transitions"}):
        raise ValueError(_UNKNOWN_BRANCH_ROLE_FIELDS_ERROR)
    return BranchRolePolicy(
        release_mirror=RELEASE_MIRROR_ACCEPTED_FF
        if raw_policy.get("release_mirror") == RELEASE_MIRROR_ACCEPTED_FF
        else "independent",
        canonical_sibling_worktrees=raw_policy.get("canonical_sibling_worktrees") is True,
    )


def strict_branch_role_policy_from_text(text: str) -> BranchRolePolicy:
    """Parse the declared branch-role settings exactly; the paradigm fixes every role name."""
    raw_policy = _strict_branch_roles(text)
    return BranchRolePolicy(
        release_mirror=str(raw_policy.get("release_mirror", "independent")),
        canonical_sibling_worktrees=raw_policy.get("canonical_sibling_worktrees") is True,
    )


def declared_role_names(text: str) -> dict[str, str]:
    """Return the legacy role names a table still declares, keyed by their field."""
    raw_policy = _strict_branch_roles(text)
    return {field: str(raw_policy[field]) for field in ROLE_NAME_FIELDS if field in raw_policy}


def _strict_branch_roles(text: str) -> dict[str, object]:
    """Validate a branch-role table; a workspace without one keeps the standard roles."""
    payload = tomllib.loads(text)
    if "branch_roles" not in payload:
        return {}
    raw_policy = payload["branch_roles"]
    if type(raw_policy) is not dict:
        raise ValueError(_STRICT_BRANCH_ROLE_TABLE_ERROR)
    if set(raw_policy) - _BRANCH_ROLE_FIELDS:
        raise ValueError(_UNKNOWN_BRANCH_ROLE_FIELDS_ERROR)
    if any(
        type(raw_policy[field]) is not str
        or not raw_policy[field]
        or raw_policy[field] != raw_policy[field].strip()
        for field in (*ROLE_NAME_FIELDS, "release_mirror")
        if field in raw_policy
    ):
        raise ValueError(_STRICT_BRANCH_ROLE_TEXT_ERROR)
    if raw_policy.get("release_mirror", "independent") not in {
        "independent",
        RELEASE_MIRROR_ACCEPTED_FF,
    }:
        raise ValueError(_STRICT_BRANCH_ROLE_MIRROR_ERROR)
    if type(raw_policy.get("canonical_sibling_worktrees", False)) is not bool:
        raise ValueError(_STRICT_BRANCH_ROLE_SIBLING_ERROR)
    return raw_policy


def load_branch_role_policy(root: Path) -> BranchRolePolicy:
    """Load branch-role policy from the current working tree."""
    path = root / ".ethos" / "workspace.toml"
    return branch_role_policy_from_text(path.read_text(encoding="utf-8") if path.exists() else "")
