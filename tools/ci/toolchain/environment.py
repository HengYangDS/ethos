"""Typed access to the single locked project execution closure."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.trust_anchor.verification import trust_anchor


def bind_commit_trust(root: Path, anchor: Path) -> None:
    """Project an operator-supplied external trust anchor without inventing signer identity."""
    resolved, gaps = trust_anchor(root, str(anchor))
    if gaps:
        raise ValueError(gaps[0])
    assert resolved is not None
    key = "gpg.ssh.allowedSignersFile"
    current = run_git(root, "config", "--local", "--get", key, check=False)
    if current.returncode or current.stdout.strip() != str(resolved):
        run_git(root, "config", "--local", key, str(resolved))
    observed = run_git(root, "config", "--local", "--get", key).stdout.strip()
    if observed != str(resolved):
        message = "ci_commit_trust_projection_failed"
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ProjectRuntime:
    """Resolve project-owned executables without ambient PATH fallback."""

    root: Path
    python: Path
    scripts: Path

    @classmethod
    def discover(cls, root: Path) -> ProjectRuntime:
        """Bind the current interpreter and its console-script directory."""
        python = Path(sys.executable).absolute()
        return cls(root.resolve(), python, python.parent)

    def script(self, name: str) -> str:
        """Return one console script from the bound project environment."""
        suffix = ".exe" if os.name == "nt" else ""
        executable = self.scripts / f"{name}{suffix}"
        if not executable.is_file():
            message = f"project executable is unavailable: {executable}"
            raise RuntimeError(message)
        return str(executable)

    def node_executable(self) -> Path:
        """Resolve Node only for a consumer that requires its executable."""
        owner = import_module("ethos.adapters.repo.runtime.materialization.input_resolution")
        return owner.resolve_node_executable()

    def npm_command(self) -> tuple[str, str]:
        """Bind npm's native CLI to the same locked Node distribution."""
        package = import_module("nodejs_wheel")
        cli = Path(str(package.__file__)).parent / "lib/node_modules/npm/bin/npm-cli.js"
        if not cli.is_file():
            message = f"project npm CLI is unavailable: {cli}"
            raise RuntimeError(message)
        return str(self.node_executable()), str(cli)

    def node_package_supply(self) -> Path:
        """Validate current locked Node supply at the capability boundary."""
        owner = import_module("ethos.adapters.repo.runtime.materialization.node_package_supply")
        return owner.resolve_node_package_supply(self.root)
