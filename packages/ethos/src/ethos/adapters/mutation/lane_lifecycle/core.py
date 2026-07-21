from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


def run_git(
    root: Path,
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    effective_env = None if env is None else {**os.environ, **env}
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
        env=effective_env,
        input=stdin,
    )


def repo_root(root: Path) -> Path:
    return Path(run_git(root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip().lower()).strip("-") or "work"


def default_candidate_path(repo: Path, candidate_branch: str) -> Path:
    return repo.with_name(f"{repo.name}-{slug(candidate_branch)}")


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = run_git(root, "merge-base", "--is-ancestor", ancestor, descendant, check=False)
    return completed.returncode == 0
