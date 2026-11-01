"""A repository's declared parameters reach the adapters of its invocation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.paradigm.parameters import parameter
from ethos.repository.paradigm.parameters import repository_parameters

if TYPE_CHECKING:
    from pathlib import Path


def test_an_invocation_reads_its_repository_values_and_otherwise_the_defaults(
    tmp_path: Path,
) -> None:
    """A bound binding's value applies; an unbound or absent binding keeps every default."""
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos/rules.toml").write_text("[paradigm.timeout]\ngit_seconds = 10\n")
    assert parameter("timeout", "git_seconds") == 30
    with repository_parameters(tmp_path):
        assert parameter("timeout", "git_seconds") == 10
        assert parameter("timeout", "gate_seconds") == 600
        with repository_parameters(tmp_path / "absent"):
            assert parameter("timeout", "git_seconds") == 30
        assert parameter("timeout", "git_seconds") == 10
    assert parameter("timeout", "git_seconds") == 30
