"""A runtime archive puts only its ETHOS console on a package manager's PATH."""

from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

import tools.ci.delivery.distribution as distribution
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from tests.support.runtime_scenarios import materialize_runtime_case

if TYPE_CHECKING:
    import pytest


def test_runtime_archive_puts_only_its_console_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The console directory holds the console alone, and that console runs ETHOS.

    The runtime's own script directory also holds its interpreter and every bundled tool.
    """
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    packages = Path(git_common_dir(repo)) / "ethos/packages" / selected.wheel_sha256
    archive = tmp_path / "ethos.tar.gz"
    distribution.package_runtime(selected.root, packages / "ethos-test.whl", archive)
    with tarfile.open(archive) as packed:
        packed.extractall(tmp_path / "package", filter="tar")

    console = tmp_path / "package" / distribution.CONSOLE_DIRECTORY / "ethos"
    if selected.platform == "windows":
        console = console.with_suffix(".cmd")
    assert list(console.parent.iterdir()) == [console]
    shown = subprocess.run(
        (str(console), "--version"), capture_output=True, text=True, check=False, timeout=60
    )
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.strip()
