"""The canonical text layout that `pre-commit` admits on staged index blobs.

The format policy's `canonical-text` rows select the files, and the layout is the one that
`ethos lane format` writes, so a commit is refused for the bytes the source-format gate refuses.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.gates.native.inputs import RECORD_PREFIXES
from ethos.adapters.gates.native.inputs import format_ownership
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_attributes import received_paths
from ethos.adapters.repo.hook.staged_size import staged_regular_files
from ethos.repository.paradigm.packages import PACKAGE_MARKER
from ethos.repository.paradigm.packages import opens_with_docstring
from ethos.repository.paradigm.parameters import seconds
from ethos.repository.paradigm.text_layout import text_layout_violation

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def check_staged_text(root: Path, *, index_env: Mapping[str, str] | None = None) -> None:
    """Refuse a staged canonical-text file whose index blob leaves the canonical layout."""
    staged = tuple(
        path
        for path in staged_regular_files(root, index_env)
        if not path.startswith(RECORD_PREFIXES)
    )
    if not staged:
        return
    ownership = format_ownership(root, staged)
    owned = {
        str(item["path"])
        for item in ownership["assignments"]
        if item["mutation_policy"] == "canonical-text"
    }
    for path in sorted(owned - received_paths(root, tuple(owned))):
        try:
            blob = run_git(
                root, "show", f":{path}", text=False, timeout=seconds("git"), env=index_env
            )
            line = text_layout_violation(blob.stdout.decode("utf-8"))
        except (subprocess.CalledProcessError, UnicodeError) as error:
            message = f"pre_commit_text_unreadable:{path}"
            raise RuntimeError(message) from error
        if line is not None:
            message = f"pre_commit_text_layout:{path}:{line + 1}"
            raise RuntimeError(message)


def check_staged_packages(root: Path, *, index_env: Mapping[str, str] | None = None) -> None:
    """Refuse a staged package marker whose index blob opens with no docstring."""
    markers = tuple(
        path
        for path in staged_regular_files(root, index_env)
        if path.rpartition("/")[2] == PACKAGE_MARKER and not path.startswith(RECORD_PREFIXES)
    )
    for path in sorted(set(markers) - received_paths(root, markers)):
        try:
            blob = run_git(
                root, "show", f":{path}", text=False, timeout=seconds("git"), env=index_env
            )
            source = blob.stdout.decode("utf-8")
        except (subprocess.CalledProcessError, UnicodeError) as error:
            message = f"pre_commit_text_unreadable:{path}"
            raise RuntimeError(message) from error
        if not opens_with_docstring(source):
            message = f"pre_commit_package_docstring:{path}"
            raise RuntimeError(message)
