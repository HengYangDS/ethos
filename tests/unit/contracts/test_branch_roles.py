"""Branch-role policy compilation boundaries."""

from __future__ import annotations

import pytest

from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import branch_role_policy_from_text
from ethos.contracts.branch.roles import strict_branch_role_policy_from_text

CURRENT = """[branch_roles]
release_branch = "main"
accepted_branch = "dev"
candidate_branch = "candidate/dev"
work_branch_prefix = "work/"
proposal_branch_prefix = "proposal/"
release_mirror = "independent"
canonical_sibling_worktrees = false
"""


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
    ("text", "error"),
    [
        ("[branch_roles\n", None),
        ("[other]\nvalue = 1\n", None),
        ("[branch_roles]\nunknown = 'x'\n", "unknown fields"),
    ],
)
def test_branch_role_observation_fails_closed_for_its_own_fields(
    text: str, error: str | None
) -> None:
    if error:
        with pytest.raises(ValueError, match=error):
            branch_role_policy_from_text(text)
    else:
        assert branch_role_policy_from_text(text) == BranchRolePolicy()


def test_branch_role_observation_ignores_retired_transition_material() -> None:
    historical = (
        CURRENT
        + """
[[branch_roles.transitions]]
id = "accepted-to-release"
source_role = "accepted_root"
target_role = "release_root"
capability = "repository.release"
required_gates = []
required_evidence = ["proof:execution"]
coupled_with = "candidate.accept"
"""
    )

    assert branch_role_policy_from_text(historical) == BranchRolePolicy(
        canonical_sibling_worktrees=False
    )
    with pytest.raises(ValueError, match="complete and exact"):
        strict_branch_role_policy_from_text(historical)


def test_branch_role_current_schema_maps_exactly() -> None:
    assert strict_branch_role_policy_from_text(CURRENT) == BranchRolePolicy(
        canonical_sibling_worktrees=False
    )


def test_a_workspace_without_the_table_keeps_the_standard_roles() -> None:
    workspace = "[commit_policy]\nsigning_required = true\n"

    assert strict_branch_role_policy_from_text(workspace) == BranchRolePolicy()
    assert (
        strict_branch_role_policy_from_text(workspace, allow_predecessor_defaults=True)
        == BranchRolePolicy()
    )
    with pytest.raises(ValueError, match="complete and exact"):
        strict_branch_role_policy_from_text('branch_roles = "main"\n')


def test_predecessor_policies_require_explicit_incumbent_compatibility() -> None:
    previous = CURRENT.replace("canonical_sibling_worktrees = false\n", "")
    oldest = previous.replace('release_mirror = "independent"\n', "")

    for table in (previous, oldest):
        with pytest.raises(ValueError, match="complete and exact"):
            strict_branch_role_policy_from_text(table)
        assert strict_branch_role_policy_from_text(
            table, allow_predecessor_defaults=True
        ) == BranchRolePolicy(canonical_sibling_worktrees=False)
    custom = oldest.replace('"candidate/dev"', '"candidate/train"')
    assert (
        strict_branch_role_policy_from_text(custom, allow_predecessor_defaults=True)
    ).candidate_branch == "candidate/train"

    incomplete = previous.replace('release_branch = "main"\n', "")
    mirrorless = CURRENT.replace('release_mirror = "independent"\n', "")
    for table in (incomplete, mirrorless, previous + "unknown = true\n"):
        with pytest.raises(ValueError, match="complete and exact"):
            strict_branch_role_policy_from_text(table, allow_predecessor_defaults=True)


@pytest.mark.parametrize(
    ("text", "error"),
    [
        (
            CURRENT.replace('release_branch = "main"', 'release_branch = " main"'),
            "canonical strings",
        ),
        (
            CURRENT.replace('release_mirror = "independent"', 'release_mirror = "mirror"'),
            "mirror is invalid",
        ),
        (
            CURRENT.replace(
                "canonical_sibling_worktrees = false",
                'canonical_sibling_worktrees = "false"',
            ),
            "must be boolean",
        ),
    ],
)
def test_branch_role_strict_value_contract(text: str, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        strict_branch_role_policy_from_text(text)


def test_branch_role_observation_defaults_invalid_values() -> None:
    report = branch_role_policy_from_text(
        "[branch_roles]\n"
        "release_branch = 1\n"
        "accepted_branch = ' '\n"
        "release_mirror = 'accepted_ff'\n"
    )
    assert (report.release_branch, report.accepted_branch, report.release_mirror) == (
        "main",
        "dev",
        "accepted_ff",
    )
