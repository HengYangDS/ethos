"""Typed access to the single locked project execution closure."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import trust_anchor


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
