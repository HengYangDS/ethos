"""The TOML that ETHOS writes into a governed repository takes the shipped Taplo layout."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.repository.release.resources as resource_owner
from ethos.adapters.gates.formatting import render_source_content
from ethos.contracts.openspec.models import OpenSpecPolicy
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from ethos.repository.toml_layout import render_toml
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_the_shipped_taplo_leaves_a_rendered_profile_unchanged(tmp_path: Path) -> None:
    """A profile with an array at the top level and one in a table is already formatted."""
    declaration = RepositoryProfileDeclaration(
        profile_id="layout",
        openspec=OpenSpecPolicy(material_paths=("**",)),
        record_roots=("evidence/",),
    )
    profile = render_repository_profile(declaration).encode()

    assert b'record_roots = [\n  "evidence/",\n]\n' in profile
    repo = init_git_repo(tmp_path / "repo")
    assert render_source_content(repo, ".ethos/profile.toml", "taplo", profile) == (profile, False)


@pytest.mark.parametrize("formatting", ['indent_string = "\\t"', 'indent_string = ""', ""])
def test_an_indent_that_is_not_spaces_refuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, formatting: str
) -> None:
    """`tomli_w` indents by spaces alone, so a tab, an empty or an absent indent is a fixed gap."""
    policy = tmp_path / "product/.config/checks/taplo/taplo.toml"
    policy.parent.mkdir(parents=True)
    policy.write_text(f"[formatting]\n{formatting}\n", encoding="utf-8")
    monkeypatch.setattr(resource_owner, "files", lambda _name: tmp_path / "product/src/ethos")

    with pytest.raises(ValueError, match="taplo_indent_not_spaces"):
        render_toml({"record_roots": ["evidence/"]})
