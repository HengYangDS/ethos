"""Provision tracked Python test fixtures before offline quality execution."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_files


def provision(root: Path) -> None:
    """Warm each fixture's own lock without retaining a second test environment."""
    root = root.resolve()
    locks = git_files(root, "tests/fixtures/**/uv.lock")
    with TemporaryDirectory(prefix="ethos-ci-fixture-supply-") as temporary:
        for index, relative in enumerate(locks):
            lock = root / relative
            project = lock.parent / "pyproject.toml"
            if (
                lock.is_symlink()
                or not lock.is_file()
                or not lock.resolve().is_relative_to(root)
                or project.is_symlink()
                or not project.is_file()
                or not project.resolve().is_relative_to(root)
            ):
                message = f"ci_fixture_project_invalid:{relative}"
                raise ValueError(message)
            environment = {
                **os.environ,
                "UV_PROJECT_ENVIRONMENT": str(Path(temporary) / str(index)),
                "UV_LINK_MODE": "copy",
            }
            result = run_command(
                root,
                (
                    sys.executable,
                    "-m",
                    "uv",
                    "--directory",
                    str(lock.parent),
                    "sync",
                    "--no-config",
                    "--locked",
                    "--no-install-project",
                    "--group",
                    "dev",
                ),
                env=environment,
                inherit_environment=False,
                timeout=120,
            )
            if result.returncode:
                detail = (result.stderr or result.stdout or "").strip()
                if detail:
                    print(detail[-2000:], file=sys.stderr)
                message = f"ci_fixture_supply_failed:{relative}:exit={result.returncode}"
                raise RuntimeError(message)


if __name__ == "__main__":
    provision(Path(sys.argv[1]))
