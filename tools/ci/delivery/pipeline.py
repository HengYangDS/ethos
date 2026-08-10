"""Build and package-conformance effects for the locked project runtime."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

from tools.ci.local_install_smoke import prepare_supply
from tools.ci.local_install_smoke import run as run_install_smoke

if TYPE_CHECKING:
    import nox

    from tools.ci.toolchain.environment import ProjectRuntime


@dataclass(frozen=True, slots=True)
class DeliveryPipeline:
    """Own wheel materialization and its package-only acceptance sequence."""

    runtime: ProjectRuntime
    node: Path
    npm_cli: Path

    @classmethod
    def from_runtime(cls, runtime: ProjectRuntime) -> DeliveryPipeline:
        """Bind the wheel's locked Node and npm build inputs."""
        supply = Path(import_module("nodejs_wheel").__file__).resolve().parent
        suffix = ".exe" if __import__("os").name == "nt" else ""
        return cls(
            runtime,
            supply / "bin" / f"node{suffix}",
            supply / "lib/node_modules/npm/bin/npm-cli.js",
        )

    def build(self, session: nox.Session) -> None:
        """Materialize exactly one offline wheel through Hatchling and uv."""
        session.run(
            self.runtime.script("uv"),
            "build",
            "--offline",
            "--wheel",
            "--out-dir",
            "build/artifacts/python",
            "--clear",
            "--no-create-gitignore",
            env={"ETHOS_BUILD_NODE": str(self.node), "ETHOS_BUILD_NPM_CLI": str(self.npm_cli)},
        )

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
