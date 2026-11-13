"""The layout rules that `pre-commit` admits on staged index blobs.

Each staged authored file meets the rule its owner applies later: a Markdown file the list rule, a
`canonical-text` file of the format policy the canonical layout, and a package marker an opening
docstring. A commit is refused for the bytes that the gates and the paradigm would refuse.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.gates.native.inputs import RECORD_PREFIXES
from ethos.adapters.gates.native.inputs import paradigm_received_paths
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.staged_size import staged_regular_files
from ethos.repository.paradigm.markdown_spacing import spacing_violations
from ethos.repository.paradigm.packages import PACKAGE_MARKER
from ethos.repository.paradigm.packages import opens_with_docstring
from ethos.repository.paradigm.parameters import seconds
from ethos.repository.paradigm.text_layout import text_layout_violation
from ethos.repository.policy.quality.format_selection import POLICY_PATH
from ethos.repository.policy.quality.format_selection import canonical_text_paths
from ethos.repository.release.resources import canonical_resource

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def check_staged_text(root: Path, *, index_env: Mapping[str, str] | None = None) -> None:
    """Refuse the first staged authored file whose index blob breaks its layout rule.

    The canonical-text rows come from the shipped policy: under an installed runtime the product's
    own repository keeps a full policy file that is not a byte-bound carrier increment.
    """
    staged = tuple(
        path
        for path in staged_regular_files(root, index_env)
        if not path.startswith(RECORD_PREFIXES)
    )
    if not staged:
        return
    canonical = canonical_text_paths(staged, canonical_resource(POLICY_PATH.as_posix()))
    for path in sorted(set(staged) - paradigm_received_paths(root, staged)):
        markdown, marker = path.endswith(".md"), path.rpartition("/")[2] == PACKAGE_MARKER
        if not (markdown or marker or path in canonical):
            continue
        try:
            blob = run_git(
                root, "show", f":{path}", text=False, timeout=seconds("git"), env=index_env
            )
            text = blob.stdout.decode("utf-8")
        except (subprocess.CalledProcessError, UnicodeError) as error:
            message = f"pre_commit_text_unreadable:{path}"
            raise RuntimeError(message) from error
        if gap := _layout_gap(path, text, markdown=markdown, marker=marker):
            raise RuntimeError(gap)


def _layout_gap(path: str, text: str, *, markdown: bool, marker: bool) -> str:
    """Name the first layout violation of one staged text, or return an empty string."""
    if markdown:
        violations = spacing_violations(text)
        return f"pre_commit_markdown_spacing:{path}:{min(violations) + 1}" if violations else ""
    if marker:
        return "" if opens_with_docstring(text) else f"pre_commit_package_docstring:{path}"
    line = text_layout_violation(text)
    return "" if line is None else f"pre_commit_text_layout:{path}:{line + 1}"
