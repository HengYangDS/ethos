"""Native quality inputs refuse unreadable owners and linked configuration instead of guessing."""

from __future__ import annotations

import pytest

import ethos.adapters.gates.native.inputs as native_inputs
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


@pytest.mark.parametrize("owner", [".ethos/profile.toml", "docs/_meta/taxonomy.toml"])
def test_authored_inputs_refuse_an_unreadable_owner(tmp_path, owner) -> None:
    """An unreadable profile or document taxonomy stops selection instead of guessing owners."""
    (tmp_path / owner).parent.mkdir(parents=True)
    (tmp_path / owner).write_text("[unterminated\n")
    with pytest.raises(ValueError, match=f"_invalid:{owner}$"):
        native_inputs.authored_source_files(tmp_path, paths=("README.md",))


def test_a_linked_tool_configuration_is_refused(tmp_path) -> None:
    """A repository configuration that links outside the root is refused, never followed."""
    repo = init_git_repo(tmp_path / "adopter")
    (repo / ".config/checks/taplo/taplo.toml").unlink()
    (repo / ".config/checks/taplo/taplo.toml").symlink_to(tmp_path / "taplo.toml")
    with pytest.raises(ValueError, match=r"^native_tool_configuration_invalid:taplo$"):
        native_inputs.native_configurations(repo, "taplo", ".config/checks/taplo/taplo.toml")


def test_a_moved_tool_configuration_selects_its_live_carrier(tmp_path) -> None:
    """A carrier deleted from the worktree but still indexed is absent; the live one binds."""
    repo = init_git_repo(tmp_path / "adopter")
    legacy = repo / ".config/checks/toml/taplo.toml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("", encoding="utf-8")
    git(repo, "add", "--", ".config/checks/toml/taplo.toml")
    legacy.unlink()
    selected = native_inputs.native_repository_configuration(repo, "taplo")
    assert selected == repo / ".config/checks/taplo/taplo.toml"


def test_two_live_tool_configurations_stay_ambiguous(tmp_path) -> None:
    """Two materialized carriers still compete, so the tool configuration is refused."""
    repo = init_git_repo(tmp_path / "adopter")
    legacy = repo / ".config/checks/toml/taplo.toml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match=r"^native_tool_configuration_ambiguous:taplo$"):
        native_inputs.native_repository_configuration(repo, "taplo")
