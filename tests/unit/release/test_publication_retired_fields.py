"""The publication declaration names peers only; retired fields refuse until repaired."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.release.publication import publication_topology

if TYPE_CHECKING:
    from pathlib import Path

_PEER = {
    "id": "gitlab",
    "provider": "gitlab",
    "role": "organization_collaboration",
    "git_remote": "gitlab",
    "capabilities": ["repository", "publication"],
}


@pytest.mark.parametrize(
    ("declaration", "field"),
    [
        ({"local_verification_command": "true", "peers": [_PEER]}, "local_verification_command"),
        ({"local_installation_command": "true", "peers": [_PEER]}, "local_installation_command"),
        (
            {"peers": [{**_PEER, "forge_repository": "https://forge.test/team/repo"}]},
            "forge_repository",
        ),
    ],
)
def test_each_retired_field_refuses_by_name(
    tmp_path: Path, declaration: dict[str, object], field: str
) -> None:
    """The gap names the field, never its value, and the peers still compile."""
    topology = publication_topology(tmp_path, {"publication": declaration})
    assert topology["state"] == "invalid"
    assert topology["required_gaps"] == [f"publication_declaration_field_retired:{field}"]
    assert [peer["id"] for peer in topology["remotes"]] == ["gitlab"]
    assert "forge.test" not in repr(topology)


@pytest.mark.parametrize("config", [{}, {"publication": {}}])
def test_an_absent_declaration_is_zero_peers(tmp_path: Path, config: dict[str, object]) -> None:
    """A repository without publication peers, or a table the repair emptied, is ready."""
    topology = publication_topology(tmp_path, config)
    assert (topology["state"], topology["remotes"], topology["required_gaps"]) == ("ready", [], [])
    assert "local" not in topology
