"""A repository's declared parameters reach the adapters of its invocation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.parameters import parameter
from ethos.repository.paradigm.parameters import parameter_resolution
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


@pytest.mark.parametrize(
    ("declared", "applied", "gaps"),
    [
        ("record_seconds = 2419200\n", 2_419_200, []),
        ("record_seconds = 86400\n", 1_209_600, ["retention-declaration"]),
        ("record_seconds = 40000000\n", 1_209_600, ["retention-declaration"]),
        ("decode_depth = 3\n", 3, []),
    ],
    ids=["floor-raised", "floor-lowered", "floor-beyond-bound", "ordinary-lowered"],
)
def test_a_retention_floor_rises_without_a_reason_and_never_falls(
    declared: str, applied: int, gaps: list[str]
) -> None:
    """A floor row inverts the ordinary rule; its other rows keep it."""
    resolution = parameter_resolution(
        f"[paradigm.retention]\n{declared}", load_repository_paradigm()
    )
    key = declared.split(" = ", maxsplit=1)[0]
    assert resolution.values["retention"][key] == applied
    assert [gap.obligation for gap in resolution.gaps] == gaps
    assert resolution.deviations == ()
