"""Select the tests that read what a change touches, from tracked text alone.

A selection says which tests to run first. It is a lower bound and never a proof: a test that
reads a file through a function and names neither the file nor its module is not found, a
deleted file has no text and so selects no importer, and only the full suite examines every
test. A name is matched as text, so a path of one word also selects each test that holds it.
"""

from __future__ import annotations

import posixpath
import tomllib
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python_syntax import complete_python_tree
from ethos.repository.policy.references.python_syntax import imported_modules
from ethos.repository.policy.references.python_syntax import module_name

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Mapping

# The wheel table of the Python manifest that names the repository files a package carries.
_CARRIED_TABLE = "force-include"
_CONFTEST = "conftest.py"
# Why a test is selected, weakest first; a test that several reasons select keeps the strongest.
_REASONS = ("stages", "names", "imports", "conftest", "changed")


def carried_paths(manifest: str) -> tuple[str, ...]:
    """Return the files and directories that the Python manifest's wheel table carries.

    A manifest without that table carries nothing; one that cannot be parsed raises its error.
    """
    try:
        wheel = tomllib.loads(manifest)["tool"]["hatch"]["build"]["targets"]["wheel"]
        return tuple(wheel[_CARRIED_TABLE])
    except (KeyError, TypeError):
        return ()


def select_tests(
    changed: Collection[str],
    files: Mapping[str, str],
    tests: frozenset[str],
    carried: tuple[str, ...] = (),
) -> tuple[dict[str, str], list[str]]:
    """Return each test that reads a changed path, with its strongest reason, and the unread paths.

    `files` holds the text of every Python file by path and `tests` names those that are tests.
    A changed test selects itself (`changed`), and a changed `conftest.py` the tests of its
    directory (`conftest`). A changed Python file selects the tests that import it, or import a
    file that imports it (`imports`). Any changed path selects the tests whose text names it
    (`names`), and a path that the package carries selects the tests whose text names the
    carried-file table, because they stage the package from it (`stages`). The files are parsed
    only when a changed path is one of them.
    """
    python = any(path in files for path in changed)
    imports = {
        path: imported_modules(path, tree)
        for path, text in (files.items() if python else ())
        if (tree := complete_python_tree(text)) is not None
    }
    selected: dict[str, str] = {}
    unread: list[str] = []
    for path in changed:
        found = _readers(path, files, tests, imports, carried)
        if not found:
            unread.append(path)
        for test, reason in found.items():
            selected[test] = max(selected.get(test, reason), reason, key=_REASONS.index)
    return {test: selected[test] for test in sorted(selected)}, sorted(unread)


def _readers(
    path: str,
    files: Mapping[str, str],
    tests: frozenset[str],
    imports: Mapping[str, set[str]],
    carried: tuple[str, ...],
) -> dict[str, str]:
    """Return each test that reads one changed path, with the strongest reason that path gives."""
    module = module_name(path) if path in imports else ""
    reach = {module} | {module_name(user) for user, names in imports.items() if module in names}
    below = posixpath.join(posixpath.dirname(path), "")
    conftest = posixpath.basename(path) == _CONFTEST
    staged = any(f"{path}/".startswith(source.rstrip("/") + "/") for source in carried)
    # One test of a reader for each reason, in the order of `_REASONS`: a later reason replaces an
    # earlier one for the same test.
    reads = (
        lambda test: staged and _CARRIED_TABLE in files.get(test, ""),
        lambda test: path in files.get(test, ""),
        lambda test: module and imports.get(test, set()) & reach,
        lambda test: conftest and test.startswith(below),
        lambda test: test == path,
    )
    return {
        test: reason
        for reason, read in zip(_REASONS, reads, strict=True)
        for test in tests
        if read(test)
    }
