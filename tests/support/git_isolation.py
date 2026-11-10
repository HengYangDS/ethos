"""The Git settings that keep every test repository inert and independent of the host."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# No test repository depends on a host filesystem monitor, and none repacks or prunes itself in a
# detached process after a commit, so its objects stay exactly as the test wrote them.
GIT_ISOLATION = (("core.fsmonitor", "false"), ("maintenance.auto", "false"))


def work_tree_refusal(basetemp: Path) -> str | None:
    """Return why a test session must not run in this base temporary directory, or None.

    Product code finds a repository by walking up from a path, so a fixture root inside a real
    checkout reads and writes that checkout's `.git/ethos` state. Git answers without any ambient
    `GIT_` variable, so a `GIT_DIR` cannot hide the enclosing repository, and only Git's own "not a
    git repository" answer means outside: any other failure refuses.
    """
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    command = [
        "git",
        "-C",
        str(basetemp),
        "rev-parse",
        "--is-inside-work-tree",
        "--is-inside-git-dir",
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, check=False, env=environment
        )
    except OSError as error:
        return f"cannot tell whether {basetemp} is inside a Git repository: {error}"
    answers = completed.stdout.split()
    if completed.returncode == 128 and "not a git repository" in completed.stderr:
        return None
    if completed.returncode or len(answers) != 2 or not set(answers) <= {"true", "false"}:
        return (
            f"cannot tell whether {basetemp} is inside a Git repository: {completed.stderr.strip()}"
        )
    if "true" not in answers:
        return None
    return (
        f"pytest's base temporary directory {basetemp} is inside a Git repository; "
        "pass --basetemp outside any repository"
    )
