"""Python package markers state their purpose: each `__init__.py` opens with a docstring.

The docstring's text is the package's purpose, which only its authors know, so a gap is
report-only. An empty or unparsable marker has no docstring.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

PACKAGE_MARKER = "__init__.py"


def opens_with_docstring(source: str | None) -> bool:
    """Return whether Python source opens with a docstring."""
    if not source:
        return False
    try:
        return ast.get_docstring(ast.parse(source)) is not None
    except SyntaxError:
        return False


def package_docstring_gaps(root: Path, tracked: frozenset[str]) -> Iterator[ParadigmGap]:
    """Report each tracked package marker that does not open with a docstring."""
    for path in sorted(tracked):
        if path.rpartition("/")[2] == PACKAGE_MARKER and not opens_with_docstring(
            tracked_text(root, path, tracked)
        ):
            yield ParadigmGap(
                "package-docstring",
                path,
                f"open {path} with a one-line docstring that names the package's purpose",
            )
