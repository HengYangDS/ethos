"""Build and package-conformance effects for the locked project runtime."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_openspec_supply
from ethos.adapters.repo.runtime.source import source_build_identity
from ethos.adapters.repo.runtime.transition import materialize_package_wheel
from tools.ci.local_install_smoke import prepare_supply
from tools.ci.local_install_smoke import run as run_install_smoke

if TYPE_CHECKING:
    import nox

    from tools.ci.toolchain.environment import ProjectRuntime


@dataclass(frozen=True, slots=True)
class DeliveryPipeline:
    """Own wheel materialization and its package-only acceptance sequence."""

    runtime: ProjectRuntime

    @classmethod
    def from_runtime(cls, runtime: ProjectRuntime) -> DeliveryPipeline:
        """Bind the delivery pipeline to the locked project runtime."""
        return cls(runtime)

    def build(self, session: nox.Session) -> None:
        """Materialize exactly one offline wheel through Hatchling and uv."""
        work = Path("build/runtime/work")
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="ethos-wheel-build-", dir=work) as directory:
            staging = Path(directory)
            session.run(
                self.runtime.script("uv"),
                "build",
                "--offline",
                "--wheel",
                "--out-dir",
                str(staging),
                "--no-create-gitignore",
                env={
                    "ETHOS_BUILD_OPENSPEC_SUPPLY": str(resolve_openspec_supply(Path.cwd())),
                },
            )
            publish_built_wheel(Path.cwd(), staging, Path("build/artifacts/python"))

    def prepare_supply(self) -> None:
        """Materialize the frozen runtime dependency supply for offline proof."""
        prepare_supply()

    def prove_install(self, session: nox.Session) -> None:
        """Install and exercise the built wheel without source-checkout fallback."""
        self.prepare_supply()
        run_install_smoke(session)

    def prove_host(self, session: nox.Session) -> None:
        """Run the complete package-only acceptance sequence on this host."""
        self.build(session)
        self.prove_install(session)
        session.run(
            str(self.runtime.python),
            "-m",
            "pytest",
            "-q",
            "tests/architecture/test_portable_toolchain.py",
            "tests/architecture/test_local_install_smoke.py",
        )


def publish_built_wheel(repo: Path, staging: Path, artifacts: Path) -> Path:
    """Admit and project exactly one wheel built from the current source identity."""
    wheels = tuple(path for path in staging.glob("ethos-*.whl") if path.is_file())
    if len(wheels) != 1:
        message = "release_wheel_output_invalid"
        raise ValueError(message)
    wheel = wheels[0]
    durable = materialize_package_wheel(
        repo,
        wheel,
        expected_build=source_build_identity(repo),
        collision="release_wheel_digest_collision",
    )
    artifacts = artifacts.resolve()
    artifacts.parent.mkdir(parents=True, exist_ok=True)
    replacement = artifacts.parent / f".{artifacts.name}-replacement"
    backup = artifacts.parent / f".{artifacts.name}-previous"
    if replacement.exists():
        shutil.rmtree(replacement)
    replacement.mkdir()
    shutil.copy2(durable.path, replacement / wheel.name)
    if backup.exists():
        shutil.rmtree(backup)
    if artifacts.exists():
        artifacts.rename(backup)
    try:
        replacement.rename(artifacts)
    except OSError:
        if backup.exists() and not artifacts.exists():
            backup.rename(artifacts)
        raise
    finally:
        shutil.rmtree(replacement, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    return artifacts / wheel.name
