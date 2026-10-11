"""Supply an explicit observer wheel and a shared Nox-only parent for native tests."""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.manifest import runtime_manifest_bytes
from ethos.adapters.repo.runtime.materialization.python_environment import (
    observe_runtime_environment,
)
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.repository.release.identity import wheel_build_identity

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True)
class NativeNoxSupply:
    """Keep shared dependencies separate from each repository's selected wheel custody."""

    wheel: Path
    wheel_sha256: str
    parent: Path
    uv: Path
    project: Path
    environments: Path

    def bind(self, root: Path) -> None:
        """Select the provided bytes through the existing test-local runtime protocol."""
        common = Path(git_common_dir(root))
        staging = common / "ethos/runtime/.native-nox"
        run_command(
            root,
            (
                str(self.uv),
                "venv",
                "--no-python-downloads",
                "--python",
                sys.executable,
                str(staging / "python"),
            ),
            timeout=15,
            check=True,
        )
        interpreter = (
            staging / "python" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        if interpreter.is_symlink():
            source = interpreter.resolve(strict=True)
            interpreter.unlink()
            shutil.copy2(source, interpreter)
        environment = observe_runtime_environment(self.project, Path(sys.executable))
        files = runtime_file_inventory(staging)
        build = wheel_build_identity(self.wheel)
        digest = runtime_digest(
            wheel_sha256=self.wheel_sha256,
            build=build,
            environment=environment,
            runtime_files=files,
        )
        (staging / "manifest.json").write_bytes(
            runtime_manifest_bytes(
                digest=digest,
                wheel_sha256=self.wheel_sha256,
                build=build,
                environment=environment,
                runtime_files=files,
            )
        )
        target = staging.parent / digest
        staging.rename(target)
        wheel = common / "ethos/packages" / self.wheel_sha256 / self.wheel.name
        wheel.parent.mkdir(parents=True)
        shutil.copyfile(self.wheel, wheel)
        with wheel.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == self.wheel_sha256
        activate_runtime(common, target)


@pytest.fixture(scope="session")
def native_nox_supply(tmp_path_factory: pytest.TempPathFactory) -> Iterator[NativeNoxSupply]:
    """Missing source-only supply skips; an explicitly supplied invalid wheel fails."""
    supplied = os.environ.get("ETHOS_TEST_OBSERVER_WHEEL")
    if not supplied:
        pytest.skip("package qualification requires ETHOS_TEST_OBSERVER_WHEEL")
    wheel = Path(supplied)
    assert wheel.is_absolute()
    assert wheel.is_file()
    assert not wheel.is_symlink()
    assert wheel.suffix == ".whl"
    with wheel.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    wheel_build_identity(wheel)
    uv = shutil.which("uv")
    assert uv is not None
    scratch = tmp_path_factory.mktemp("native-nox-supply")
    parent = scratch / "parent"
    project = scratch / "floor"
    project.mkdir()
    fixture = Path(__file__).resolve().parents[4] / "fixtures/quality-sample"
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(fixture / name, project / name)
    try:
        run_command(
            scratch,
            (uv, "venv", "--no-python-downloads", "--python", sys.executable, str(parent)),
            timeout=15,
            check=True,
        )
        python = parent / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run_command(
            scratch,
            (uv, "pip", "install", "--offline", "--python", str(python), f"nox=={version('nox')}"),
            timeout=30,
            check=True,
        )
        run_command(
            scratch,
            (
                str(python),
                "-B",
                "-I",
                "-c",
                "import importlib.util; assert importlib.util.find_spec('ethos') is None",
            ),
            timeout=10,
            check=True,
        )
        yield NativeNoxSupply(wheel, digest, python, Path(uv), project, scratch / "children")
        run_command(
            scratch,
            (
                str(python),
                "-B",
                "-I",
                "-c",
                "import importlib.util; assert importlib.util.find_spec('ethos') is None",
            ),
            timeout=10,
            check=True,
        )
    finally:
        shutil.rmtree(scratch)
        assert not scratch.exists()
