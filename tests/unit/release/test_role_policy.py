"""Release declaration and role consistency independent of product packaging."""

from pathlib import Path

import pytest

import ethos.repository.release.configuration as configuration
from ethos.contracts.branch.roles import BranchRolePolicy


def _release(root: Path, source: str) -> None:
    path = root / ".ethos/release.toml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(source, encoding="utf-8")


@pytest.mark.parametrize(
    "source",
    [
        "[invalid",
        "protected_refs = false\n",
        '[protected_refs]\nbranches = "dev"\n',
        '[protected_refs]\nbranches = ["dev", "dev"]\n',
        '[protected_refs]\nbranches = [" dev"]\n',
        "[protected_refs]\ntags = [1]\n",
        '[protected_refs]\ntags = ["v*", "v*"]\n',
    ],
)
def test_present_invalid_release_is_not_absent(tmp_path: Path, source: str) -> None:
    """Every consumer receives a stable failure instead of an empty declaration."""
    _release(tmp_path, source)
    with pytest.raises(ValueError, match="release_config_invalid"):
        configuration.release_config(tmp_path)


def test_missing_release_adds_no_generic_constraint(tmp_path: Path) -> None:
    """Minimal adopters do not inherit ETHOS release packaging requirements."""
    assert configuration.release_config(tmp_path) == {}
    report = configuration.release_role_policy_report(tmp_path)
    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["protected_refs"] == {}


@pytest.mark.parametrize(
    ("branches", "expected"),
    [
        ('["main", "dev"]', []),
        ('["dev", "main"]', []),
        ('["dev"]', ["protected_branches_policy_missing"]),
        ('["main", "dev", "candidate/dev"]', ["protected_branches_policy_missing"]),
    ],
)
def test_generic_release_role_membership(
    tmp_path: Path, branches: str, expected: list[str]
) -> None:
    """Membership, not sequence or gate storage, determines role consistency."""
    _release(tmp_path, f"[protected_refs]\nbranches = {branches}\ntags = []\n")
    report = configuration.release_role_policy_report(tmp_path)
    assert report["required_gaps"] == expected
    assert report["verdict"] == ("block" if expected else "pass")
    assert "version" not in report


def test_generic_roles_follow_configured_names(tmp_path: Path) -> None:
    """Role policy, rather than conventional names, owns protected branches."""
    _release(tmp_path, '[protected_refs]\nbranches = ["integration", "stable"]\n')
    (tmp_path / ".ethos/workspace.toml").write_text(
        '[branch_roles]\nrelease_branch = "stable"\naccepted_branch = "integration"\n',
        encoding="utf-8",
    )
    assert configuration.release_role_policy_report(tmp_path)["verdict"] == "pass"


def test_product_report_preserves_generic_invalid_gap(tmp_path: Path) -> None:
    """Product reporting retains parse failure without raising or pretending absence."""
    _release(tmp_path, "[invalid")
    report = configuration.release_policy_report(tmp_path)
    assert report["verdict"] == "block"
    assert report["required_gaps"].count("release_config_invalid:.ethos/release.toml") == 1


def test_pure_role_validation_accepts_equivalent_declaration() -> None:
    """Git-tree consumers share the same compiler as filesystem observations."""
    config = configuration.release_config_from_text(
        '[protected_refs]\nbranches = ["dev", "main"]\ntags = []\n'
    )
    assert configuration.release_role_policy_gaps(config, BranchRolePolicy()) == []
