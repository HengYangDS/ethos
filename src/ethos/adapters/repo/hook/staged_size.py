"""The per-file code ceiling that `pre-commit` admits on staged index blobs.

The measure and the resolved ceiling are the paradigm report's, so a commit is refused for the
bytes that readiness would refuse later.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_attributes import received_paths
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.parameters import parameter
from ethos.repository.paradigm.parameters import seconds
from ethos.repository.paradigm.size import effective_lines

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

# A symlink or gitlink entry holds no source of its own.
_REGULAR_FILE_MODES = frozenset({b"100644", b"100755"})


def check_staged_sizes(root: Path, *, index_env: Mapping[str, str] | None = None) -> None:
    """Refuse a staged authored file whose index blob exceeds the per-file code ceiling."""
    paradigm = load_repository_paradigm()
    languages = {
        path: language
        for path in _staged_files(root, index_env)
        if (language := paradigm.language_of(path)) is not None
    }
    ceiling = parameter("size", "code_effective_lines")
    for path in sorted(set(languages) - received_paths(root, tuple(languages))):
        try:
            blob = run_git(
                root, "show", f":{path}", text=False, timeout=seconds("git"), env=index_env
            )
            lines = effective_lines(languages[path], blob.stdout.decode("utf-8"))
        except (subprocess.CalledProcessError, UnicodeError, SyntaxError, ValueError) as error:
            message = f"pre_commit_code_size_unmeasurable:{path}"
            raise RuntimeError(message) from error
        if lines > ceiling:
            message = f"pre_commit_code_size_exceeded:{path}:{lines}>{ceiling}"
            raise RuntimeError(message)


def _staged_files(root: Path, index_env: Mapping[str, str] | None) -> tuple[str, ...]:
    """Return the regular files that the index adds, copies, modifies, renames or retypes."""
    completed = run_git(
        root,
        "diff",
        "--cached",
        "--raw",
        "--no-renames",
        "--diff-filter=ACMRT",
        "-z",
        text=False,
        timeout=seconds("git"),
        env=index_env,
    )
    # Each record is `:<old mode> <new mode> <old id> <new id> <status>` and then its path.
    fields = completed.stdout.split(b"\0")[:-1]
    return tuple(
        path.decode("utf-8", errors="surrogateescape")
        for record, path in zip(fields[::2], fields[1::2], strict=True)
        if record.split()[1] in _REGULAR_FILE_MODES
    )
