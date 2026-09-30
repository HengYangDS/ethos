"""Reject ambiguous native command frames before any repository execution."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.python.nox as native_nox

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "command",
    [
        ("uv", "run", "--locked", "--python", "nox", "echo", "not-a-session"),
        ("uv", "run", "--locked", "--group", "nox", "echo"),
        ("uv", "run", "--locked", "--project", "nox", "echo"),
        ("uv", "run", "--no-sync", "nox", "-s", "tests"),
        ("mise", "exec", "--", "uv", "run", "--locked", "nox"),
    ],
)
def test_nox_preflight_rejects_option_values_masquerading_as_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: tuple[str, ...]
) -> None:
    """A token spelling 'nox' is not the invoked module or executable."""
    observed: list[tuple[str, ...]] = []

    def supply(_root: Path, argv: tuple[str, ...], **_kwargs: object):
        observed.append(argv)
        return subprocess.CompletedProcess(argv, 0, "7.16.2\n", "")

    monkeypatch.setattr(native_nox, "run_command", supply)

    with pytest.raises(ValueError, match=r"python_nox_command_(?:unsupported|unlocked)"):
        native_nox.preflight(tmp_path, command)

    assert observed == []


@pytest.mark.parametrize("option", ["--report=foreign.json", "--envdir=foreign", "--usage=tests"])
def test_nox_preflight_rejects_output_and_nonexecution_mode_overrides(
    tmp_path: Path, option: str
) -> None:
    """Native option syntax cannot bypass ownership of the attempt's outputs."""
    with pytest.raises(ValueError, match="python_nox_output_selection_conflict"):
        native_nox.preflight(tmp_path, (sys.executable, "-m", "nox", option))
