"""Branch-role policy compilation boundaries."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import branch_role_policy_from_release_text
from ethos.contracts.branch.roles import declared_role_names
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.branch.roles import strict_branch_role_policy_from_release_text
from ethos.contracts.branch.roles import strict_source_branch_role_policy

if TYPE_CHECKING:
    from pathlib import Path

LEGACY = """[branch_roles]
release_branch = "main"
accepted_branch = "dev"
candidate_branch = "candidate/train"
work_branch_prefix = "work/"
proposal_branch_prefix = "submit/"
release_mirror = "accepted_ff"
canonical_sibling_worktrees = false
"""
ACCEPTED_FF = BranchRolePolicy(release_mirror="accepted_ff")


@pytest.mark.parametrize(
    ("branch", "topic"),
    [
        ("work/one", True),
        ("codex/one", True),
        ("topic/one", True),
        ("proposal/one", True),
        ("dev", False),
        ("main", False),
        ("candidate/dev", False),
        ("detached", False),
        ("", False),
    ],
)
def test_topic_identity_is_not_authoring_permission(branch: str, *, topic: bool) -> None:
    policy = BranchRolePolicy()
    assert policy.is_topic_branch(branch) is topic
    if branch in {"codex/one", "topic/one", "proposal/one"}:
        assert policy.role_for_branch(branch) == "other"


@pytest.mark.parametrize(
    ("release", "policy"),
    [
        ("", BranchRolePolicy()),
        ('[release]\nmirror = "accepted_ff"\n', ACCEPTED_FF),
        ('[release]\nmirror = "independent"\n', BranchRolePolicy()),
        ('[release]\nversion_source = "VERSION"\n', BranchRolePolicy()),
        ('[protected_refs]\ntags = ["v*"]\n', BranchRolePolicy()),
    ],
    ids=["absent", "accepted-ff", "independent", "other-release-facts", "no-release-table"],
)
def test_the_release_binding_declares_the_mirror(release: str, policy: BranchRolePolicy) -> None:
    """Only `[release] mirror` selects the mirror; every role name stays the paradigm's."""
    assert strict_branch_role_policy_from_release_text(release) == policy
    assert branch_role_policy_from_release_text(release) == policy


@pytest.mark.parametrize(
    ("release", "error"),
    [
        ('release = "accepted_ff"\n', "must be a table"),
        ('[release]\nmirror = "mirror"\n', "mirror is invalid"),
        ("[release]\nmirror = 1\n", "mirror is invalid"),
    ],
)
def test_the_strict_reader_refuses_an_invalid_mirror(release: str, error: str) -> None:
    """Admission fails closed on a mirror it cannot honor; observation keeps the default."""
    with pytest.raises(ValueError, match=error):
        strict_branch_role_policy_from_release_text(release)
    assert branch_role_policy_from_release_text(release) == BranchRolePolicy()


def test_unreadable_release_text_keeps_the_standard_policy_for_observation() -> None:
    assert branch_role_policy_from_release_text("[release\n") == BranchRolePolicy()
    with pytest.raises(ValueError, match="Expected"):
        strict_branch_role_policy_from_release_text("[release\n")


def test_a_workspace_mirror_is_a_retired_declaration(tmp_path: Path) -> None:
    """The working tree's release binding decides the mirror; a workspace table no longer does."""
    binding = tmp_path / ".ethos"
    binding.mkdir()
    (binding / "workspace.toml").write_text(LEGACY, encoding="utf-8")
    assert load_branch_role_policy(tmp_path) == BranchRolePolicy()
    (binding / "release.toml").write_text('[release]\nmirror = "accepted_ff"\n', encoding="utf-8")
    assert load_branch_role_policy(tmp_path) == ACCEPTED_FF


@pytest.mark.parametrize(
    ("workspace", "release", "policy"),
    [
        ('[branch_roles]\nrelease_mirror = "accepted_ff"\n', "", ACCEPTED_FF),
        (LEGACY, "", ACCEPTED_FF),
        ("", '[release]\nmirror = "accepted_ff"\n', ACCEPTED_FF),
        ('[branch_roles]\naccepted_branch = "dev"\n', "", BranchRolePolicy()),
        ("", "", BranchRolePolicy()),
    ],
    ids=["earlier-location", "earlier-table", "current-location", "names-only", "absent"],
)
def test_a_source_commit_keeps_its_own_mirror_location(
    workspace: str, release: str, policy: BranchRolePolicy
) -> None:
    """Historical evidence reads the mirror where its source commit declared it (DR-0013)."""
    assert strict_source_branch_role_policy(release, workspace) == policy


@pytest.mark.parametrize(
    ("workspace", "release", "error"),
    [
        (LEGACY, '[release]\nmirror = "accepted_ff"\n', "declared twice"),
        ('[branch_roles]\nrelease_mirror = "mirror"\n', "", "mirror is invalid"),
        ('branch_roles = "main"\n', "", "must be a table"),
        ("", '[release]\nmirror = "mirror"\n', "mirror is invalid"),
    ],
)
def test_the_source_mirror_reader_fails_closed(workspace: str, release: str, error: str) -> None:
    """A commit that declares both locations, or an invalid mirror, selects neither."""
    with pytest.raises(ValueError, match=error):
        strict_source_branch_role_policy(release, workspace)


def test_legacy_role_names_come_from_the_workspace_table() -> None:
    """Closeout renames the refs a workspace still names; retired settings are not read."""
    assert declared_role_names(LEGACY) == {
        "release_branch": "main",
        "accepted_branch": "dev",
        "candidate_branch": "candidate/train",
        "work_branch_prefix": "work/",
        "proposal_branch_prefix": "submit/",
    }
    assert declared_role_names("[commit_policy]\nsigning_required = true\n") == {}
    retired = '[branch_roles]\nrelease_mirror = "mirror"\ncanonical_sibling_worktrees = "x"\n'
    assert declared_role_names(retired) == {}


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ('branch_roles = "main"\n', "must be a table"),
        (LEGACY + "unknown = true\n", "unknown fields"),
        (
            LEGACY.replace('release_branch = "main"', 'release_branch = " main"'),
            "canonical strings",
        ),
        (LEGACY.replace('accepted_branch = "dev"', "accepted_branch = 1"), "canonical strings"),
    ],
)
def test_the_legacy_name_reader_fails_closed(text: str, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        declared_role_names(text)
