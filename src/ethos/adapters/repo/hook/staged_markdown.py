"""The Markdown list rule that `pre-commit` admits on staged index blobs.

The rule is the paradigm's, so a commit is refused for the bytes that the Markdown gate would
refuse later.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.gates.native.inputs import RECORD_PREFIXES
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_attributes import received_paths
from ethos.adapters.repo.hook.staged_size import staged_regular_files
from ethos.repository.paradigm.markdown_spacing import spacing_violations
from ethos.repository.paradigm.parameters import seconds

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def check_staged_markdown(root: Path, *, index_env: Mapping[str, str] | None = None) -> None:
    """Refuse a staged authored Markdown file whose index blob breaks the list rule."""
    markdown = tuple(
        path
        for path in staged_regular_files(root, index_env)
        if path.endswith(".md") and not path.startswith(RECORD_PREFIXES)
    )
    for path in sorted(set(markdown) - received_paths(root, markdown)):
        try:
            blob = run_git(
                root, "show", f":{path}", text=False, timeout=seconds("git"), env=index_env
            )
            violations = spacing_violations(blob.stdout.decode("utf-8"))
        except (subprocess.CalledProcessError, UnicodeError) as error:
            message = f"pre_commit_markdown_unreadable:{path}"
            raise RuntimeError(message) from error
        if violations:
            message = f"pre_commit_markdown_spacing:{path}:{min(violations) + 1}"
            raise RuntimeError(message)
