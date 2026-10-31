"""A runtime archive puts only its ETHOS console on a package manager's PATH."""

from __future__ import annotations

import json
import subprocess
import tarfile
from pathlib import Path
from pathlib import PurePosixPath
from pathlib import PureWindowsPath
from typing import TYPE_CHECKING

import tools.ci.delivery.distribution as distribution
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from tests.support.runtime_scenarios import materialize_runtime_case

if TYPE_CHECKING:
    import pytest

    from ethos.adapters.repo.runtime.selection import SelectedRuntime

# CreateProcess starts python.exe only within MAX_PATH; adopters' install prefixes need the rest.
_WINDOWS_INTERPRETER_BUDGET = 64


def _package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, SelectedRuntime, Path]:
    """Archive one materialized runtime as the release builder does."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    packages = Path(git_common_dir(repo)) / "ethos/packages" / selected.wheel_sha256
    archive = tmp_path / "ethos.tar.gz"
    distribution.package_runtime(selected.root, packages / "ethos-test.whl", archive)
    return repo, selected, archive


def test_runtime_archive_puts_only_its_console_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The console directory holds the console alone, and that console runs its own runtime.

    The runtime's own script directory also holds its interpreter and every bundled tool. A
    repository without a selection keeps the console on the archive's runtime.
    """
    repo, selected, archive = _package(tmp_path, monkeypatch)
    with tarfile.open(archive) as packed:
        packed.extractall(tmp_path / "package", filter="tar")

    console = tmp_path / "package" / distribution.CONSOLE_DIRECTORY / "ethos"
    if selected.platform == "windows":
        console = console.with_suffix(".cmd")
    assert list(console.parent.iterdir()) == [console]
    command = (str(console), "--version", "--json", "--root", str(repo))
    shown = subprocess.run(command, capture_output=True, text=True, check=False, timeout=60)
    assert shown.returncode == 0, shown.stderr
    assert json.loads(shown.stdout)["data"]["identity"]["runtime_digest"] == selected.digest


def test_archive_keeps_its_windows_interpreter_path_within_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The archive's part of the Windows interpreter path leaves the install prefix the rest."""
    _repo, _selected, archive = _package(tmp_path, monkeypatch)
    with tarfile.open(archive) as packed:
        (runtime,) = {
            path.parent
            for path in map(PurePosixPath, packed.getnames())
            if path.parts[:2] == ("ethos", "runtime") and path.parts[3:] == ("manifest.json",)
        }
    interpreter = PureWindowsPath(*runtime.parts, "python", "python.exe")
    assert len(str(interpreter)) <= _WINDOWS_INTERPRETER_BUDGET, interpreter
