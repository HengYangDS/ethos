from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path

ROLE_RELEASE_ROOT = "release_root"
ROLE_ACCEPTED_ROOT = "accepted_root"
ROLE_CANDIDATE = "candidate"
ROLE_WORK_LANE = "work_lane"
ROLE_SUBMIT_LANE = "submit_lane"
ROLE_DETACHED = "detached"
ROLE_OTHER = "other"

RELEASE_MIRROR_ACCEPTED_FF = "accepted_ff"

PROTECTED_WRITE_ROLES = frozenset(
    {
        ROLE_RELEASE_ROOT,
        ROLE_ACCEPTED_ROOT,
        ROLE_CANDIDATE,
        ROLE_SUBMIT_LANE,
        ROLE_DETACHED,
        ROLE_OTHER,
    }
)


@dataclass(frozen=True)
class BranchRolePolicy:
    release_branch: str = "main"
    accepted_branch: str = "dev"
    candidate_branch: str = "candidate/dev"
    work_branch_prefix: str = "work/"
    submit_branch_prefix: str = "submit/"
    release_mirror: str = "independent"

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
        prefix_roles = (
            (self.work_branch_prefix, ROLE_WORK_LANE),
            (self.submit_branch_prefix, ROLE_SUBMIT_LANE),
        )
        return next(
            (role for prefix, role in prefix_roles if prefix and branch.startswith(prefix)),
            ROLE_OTHER,
        )

    def work_branch(self, slug: str) -> str:
        return f"{self.work_branch_prefix}{slug}"

    def submit_branch_for_source(self, branch: str) -> str:
        if not self.work_branch_prefix or not branch.startswith(self.work_branch_prefix):
            return ""
        return f"{self.submit_branch_prefix}{branch.removeprefix(self.work_branch_prefix)}"

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
            {
                "role": ROLE_SUBMIT_LANE,
                "kind": "branch_prefix",
                "config_key": "submit_branch_prefix",
                "pattern": f"{self.submit_branch_prefix}*",
            },
        )

    def as_status_policy(self) -> dict[str, object]:
        return {
            "release_branch": self.release_branch,
            "accepted_branch": self.accepted_branch,
            "candidate_branch": self.candidate_branch,
            "work_branch_prefix": self.work_branch_prefix,
            "submit_branch_prefix": self.submit_branch_prefix,
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
    default = BranchRolePolicy()
    return BranchRolePolicy(
        release_branch=_string_value(raw_policy.get("release_branch"), default.release_branch),
        accepted_branch=_string_value(raw_policy.get("accepted_branch"), default.accepted_branch),
        candidate_branch=_string_value(
            raw_policy.get("candidate_branch"), default.candidate_branch
        ),
        work_branch_prefix=_string_value(
            raw_policy.get("work_branch_prefix"), default.work_branch_prefix
        ),
        submit_branch_prefix=_string_value(
            raw_policy.get("submit_branch_prefix"), default.submit_branch_prefix
        ),
        release_mirror=RELEASE_MIRROR_ACCEPTED_FF
        if raw_policy.get("release_mirror") == RELEASE_MIRROR_ACCEPTED_FF
        else "independent",
    )


def load_branch_role_policy(root: Path) -> BranchRolePolicy:
    """Load branch-role policy from the current working tree."""
    path = root / ".ethos" / "workspace.toml"
    return branch_role_policy_from_text(path.read_text(encoding="utf-8") if path.exists() else "")


def _string_value(value: Any, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    stripped = value.strip()
    return stripped or fallback
