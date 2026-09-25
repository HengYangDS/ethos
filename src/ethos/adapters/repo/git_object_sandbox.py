"""Own bounded Git object composition without changing source refs or files."""

from __future__ import annotations

import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_executable
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.filesystem import remove_owned_path

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator


@contextmanager
def isolated_git_objects(
    root: Path, *, timeout: float = 30
) -> Iterator[Callable[..., subprocess.CompletedProcess[Any]]]:
    """Expose one temporary native object store with source objects read-only."""
    deadline = monotonic() + timeout

    def remaining_seconds() -> float:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(("git",), timeout)
        return remaining

    coordinates = run_git(
        root,
        "rev-parse",
        "--path-format=absolute",
        "--git-path",
        "objects",
        "--show-object-format",
        observation=True,
        timeout=remaining_seconds(),
        check=False,
    )
    values = coordinates.stdout.splitlines()
    if coordinates.returncode or len(values) != 2 or values[1] not in {"sha1", "sha256"}:
        message = "git_object_source_unavailable"
        raise ValueError(message)
    objects, object_format = Path(values[0]), values[1]
    if not objects.is_absolute() or not objects.is_dir():
        message = "git_object_source_unavailable"
        raise ValueError(message)
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "ETHOS Candidate",
        "GIT_AUTHOR_EMAIL": "candidate@example.invalid",
        "GIT_AUTHOR_DATE": "@0 +0000",
        "GIT_COMMITTER_NAME": "ETHOS Candidate",
        "GIT_COMMITTER_EMAIL": "candidate@example.invalid",
        "GIT_COMMITTER_DATE": "@0 +0000",
        **{
            name: os.environ[name]
            for name in ("SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP")
            if os.name == "nt" and name in os.environ
        },
    }
    executable = git_executable(environment)
    isolated = Path(tempfile.mkdtemp(prefix="ethos-objects-"))
    try:

        def git(
            *args: str, stdin: str | bytes | None = None, text: bool = True
        ) -> subprocess.CompletedProcess[Any]:
            return run_command(
                isolated,
                (executable, *args),
                text=text,
                env=environment,
                inherit_environment=False,
                stdin=stdin,
                timeout=remaining_seconds(),
            )

        initialized = git("init", "--bare", "--template=", f"--object-format={object_format}")
        if initialized.returncode:
            message = "git_object_sandbox_init_failed"
            raise ValueError(message)
        (isolated / "objects/info/alternates").write_text(
            objects.resolve().as_posix() + "\n", encoding="utf-8"
        )
        yield git
    finally:
        remove_owned_path(isolated)
