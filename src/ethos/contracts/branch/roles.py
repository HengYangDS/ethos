"""Define strict branch roles and their repository policy interpretation.

The repository paradigm fixes every role name: release `main`, accepted `dev`,
candidate `candidate/dev`, Work Lanes under `work/` and proposals under
`proposal/`, with each Work Lane in a sibling worktree. The release binding
declares the one open setting, `[release] mirror`. A `[branch_roles]` table in
the workspace binding is a retired declaration that the policy readers ignore;
accepted closeout still renames a legacy role ref it names to the paradigm's name,
and historical repair evidence still reads a mirror an earlier commit declared there.
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
# The roles in which ETHOS itself creates commits, so each needs a local signer.
LIFECYCLE_COMMIT_ROLES = frozenset({ROLE_ACCEPTED_ROOT, ROLE_CANDIDATE, ROLE_WORK_LANE})

RELEASE_MIRROR_INDEPENDENT = "independent"
RELEASE_MIRROR_ACCEPTED_FF = "accepted_ff"
_RELEASE_MIRRORS = frozenset({RELEASE_MIRROR_INDEPENDENT, RELEASE_MIRROR_ACCEPTED_FF})
_STRICT_RELEASE_TABLE_ERROR = "release must be a table"
_STRICT_RELEASE_MIRROR_ERROR = "release mirror is invalid"
_DUPLICATE_RELEASE_MIRROR_ERROR = "release mirror is declared twice"
_STRICT_BRANCH_ROLE_TABLE_ERROR = "branch_roles must be a table"
_STRICT_BRANCH_ROLE_TEXT_ERROR = "branch_roles text fields must be canonical strings"
_UNKNOWN_BRANCH_ROLE_FIELDS_ERROR = "branch_roles contains unknown fields"
ROLE_NAME_FIELDS = (
    "release_branch",
    "accepted_branch",
    "candidate_branch",
    "work_branch_prefix",
    "proposal_branch_prefix",
)
SIBLING_WORKTREE_FIELD = "canonical_sibling_worktrees"
RELEASE_MIRROR_FIELD = "release_mirror"
RETIRED_BRANCH_ROLE_FIELDS = (*ROLE_NAME_FIELDS, SIBLING_WORKTREE_FIELD, RELEASE_MIRROR_FIELD)
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
    release_mirror: str = RELEASE_MIRROR_INDEPENDENT

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


def branch_role_policy_from_release_text(text: str) -> BranchRolePolicy:
    """Observe the policy a release binding selects; text it cannot honor selects none."""
    try:
        return strict_branch_role_policy_from_release_text(text)
    except ValueError:
        return BranchRolePolicy()


def strict_branch_role_policy_from_release_text(text: str) -> BranchRolePolicy:
    """Read the release mirror a release binding declares exactly; the paradigm fixes the rest."""
    release = tomllib.loads(text).get("release", {})
    if type(release) is not dict:
        raise ValueError(_STRICT_RELEASE_TABLE_ERROR)
    mirror = release.get("mirror", RELEASE_MIRROR_INDEPENDENT)
    if type(mirror) is not str or mirror not in _RELEASE_MIRRORS:
        raise ValueError(_STRICT_RELEASE_MIRROR_ERROR)
    return BranchRolePolicy(release_mirror=mirror)


def strict_source_branch_role_policy(release_text: str, workspace_text: str) -> BranchRolePolicy:
    """Read the release mirror where one source commit declared it, for its historical evidence.

    A commit that declared `release_mirror` in the retired `[branch_roles]` table keeps that
    meaning; one that declares `[release] mirror` uses the current location. A commit that
    declares both is refused rather than choosing one (DR-0013).
    """
    policy = strict_branch_role_policy_from_release_text(release_text)
    retired = tomllib.loads(workspace_text).get("branch_roles", {})
    if type(retired) is not dict:
        raise ValueError(_STRICT_BRANCH_ROLE_TABLE_ERROR)
    if RELEASE_MIRROR_FIELD not in retired:
        return policy
    if "mirror" in tomllib.loads(release_text).get("release", {}):
        raise ValueError(_DUPLICATE_RELEASE_MIRROR_ERROR)
    mirror = retired[RELEASE_MIRROR_FIELD]
    if type(mirror) is not str or mirror not in _RELEASE_MIRRORS:
        raise ValueError(_STRICT_RELEASE_MIRROR_ERROR)
    return BranchRolePolicy(release_mirror=mirror)


def declared_role_names(text: str) -> dict[str, str]:
    """Return the legacy role names a workspace table still declares, keyed by their field."""
    payload = tomllib.loads(text)
    if "branch_roles" not in payload:
        return {}
    raw_policy = payload["branch_roles"]
    if type(raw_policy) is not dict:
        raise ValueError(_STRICT_BRANCH_ROLE_TABLE_ERROR)
    if set(raw_policy) - set(RETIRED_BRANCH_ROLE_FIELDS):
        raise ValueError(_UNKNOWN_BRANCH_ROLE_FIELDS_ERROR)
    names = {field: raw_policy[field] for field in ROLE_NAME_FIELDS if field in raw_policy}
    if any(type(name) is not str or not name or name != name.strip() for name in names.values()):
        raise ValueError(_STRICT_BRANCH_ROLE_TEXT_ERROR)
    return {field: str(name) for field, name in names.items()}


def load_branch_role_policy(root: Path) -> BranchRolePolicy:
    """Load branch-role policy from the release binding in the current working tree."""
    path = root / ".ethos" / "release.toml"
    return branch_role_policy_from_release_text(
        path.read_text(encoding="utf-8") if path.exists() else ""
    )
