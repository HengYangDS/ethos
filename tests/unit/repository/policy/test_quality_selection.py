"""A change selects the tests that read it, from tracked text alone, and names what none reads."""

from __future__ import annotations

from pathlib import Path

import pytest

from ethos.repository.policy.quality.selection import carried_paths
from ethos.repository.policy.quality.selection import select_tests

_FILES = {
    "src/pkg/core.py": "VALUE = 1\n",
    "src/pkg/near.py": "from pkg import core\n",
    "src/pkg/far.py": "from pkg.near import core\n",
    "src/pkg/sub/leaf.py": "from .. import core\n",
    "tests/test_core.py": "import pkg.core\n",
    "tests/test_near.py": "from pkg.near import core\n",
    "tests/test_far.py": "import pkg.far\n",
    "tests/test_leaf.py": "from pkg.sub import leaf\n",
    "tests/test_doc.py": "PAGE = 'docs/guide.md'\n",
    "tests/test_package.py": "TABLE = 'force-include'\n",
    "tests/unit/conftest.py": "",
    "tests/unit/test_broken.py": "def broken(:\n    'docs/guide.md'\n",
}
_TESTS = frozenset(path for path in _FILES if path.startswith("tests/"))
_CARRIED = ("docs/guide.md", "rules")
_NAMED = {"tests/test_doc.py": "names", "tests/unit/test_broken.py": "names"}
_IMPORTING = dict.fromkeys(
    ("tests/test_core.py", "tests/test_leaf.py", "tests/test_near.py"), "imports"
)


@pytest.mark.parametrize(
    ("changed", "selected", "unread"),
    [
        (["docs/guide.md"], {**_NAMED, "tests/test_package.py": "stages"}, []),
        (["rules/common.md"], {"tests/test_package.py": "stages"}, []),
        (["docs/other.md", "rules-old/a.md"], {}, ["docs/other.md", "rules-old/a.md"]),
        (["src/pkg/core.py"], _IMPORTING, []),
        (["src/pkg/far.py"], {"tests/test_far.py": "imports"}, []),
        (["src/pkg/gone.py"], {}, ["src/pkg/gone.py"]),
        (["tests/test_far.py"], {"tests/test_far.py": "changed"}, []),
        (
            ["tests/unit/conftest.py"],
            {"tests/unit/conftest.py": "changed", "tests/unit/test_broken.py": "conftest"},
            [],
        ),
        (
            ["docs/other.md", "src/pkg/core.py", "tests/test_core.py", "docs/guide.md"],
            {
                **_IMPORTING,
                **_NAMED,
                "tests/test_core.py": "changed",
                "tests/test_package.py": "stages",
            },
            ["docs/other.md"],
        ),
    ],
    ids=[
        "named-and-carried-document",
        "under-a-carried-directory",
        "no-reader",
        "module-and-its-direct-importers",
        "two-imports-away-is-not-selected",
        "deleted-module",
        "changed-test",
        "conftest-selects-its-directory",
        "union-keeps-the-strongest-reason",
    ],
)
def test_a_change_selects_its_readers_and_names_the_paths_without_one(
    changed: list[str], selected: dict[str, str], unread: list[str]
) -> None:
    """Each reason is read from tracked text: the change itself, an import, a name, the package."""
    assert select_tests(changed, _FILES, _TESTS, _CARRIED) == (selected, unread)


def test_a_root_conftest_selects_every_test() -> None:
    """A conftest at the root of the tests reaches each test below it."""
    files = {**_FILES, "conftest.py": ""}
    selected, unread = select_tests(["conftest.py"], files, _TESTS | {"conftest.py"}, ())
    assert selected == {"conftest.py": "changed", **dict.fromkeys(sorted(_TESTS), "conftest")}
    assert unread == []


@pytest.mark.parametrize(
    ("manifest", "carried"),
    [
        (
            '[tool.hatch.build.targets.wheel.force-include]\n"docs/a.md" = "a"\nrules = "r"\n',
            ("docs/a.md", "rules"),
        ),
        ('[project]\nname = "p"\n', ()),
        ("[tool.hatch.build.targets.wheel]\nforce-include = 3\n", ()),
        ("", ()),
    ],
    ids=["declared", "no-table", "not-a-table", "no-manifest"],
)
def test_the_carried_paths_come_from_the_wheel_table_or_are_none(
    manifest: str, carried: tuple[str, ...]
) -> None:
    """A manifest without a carried-file table carries nothing; an unparsable one says so."""
    assert carried_paths(manifest) == carried
    with pytest.raises(ValueError, match="line 1"):
        carried_paths("not = [toml")


def test_a_carried_document_of_this_repository_selects_the_tests_that_stage_the_package() -> None:
    """The case of 2026-11-15: a carried page's link failed a test that imports no changed file."""
    root = Path(__file__).resolve().parents[4]
    staging = (
        "tests/unit/release/test_version_identity.py",
        "tests/unit/repository/test_context.py",
    )
    naming = "tests/architecture/test_product_design_contract.py"
    files = {path: (root / path).read_text(encoding="utf-8") for path in (*staging, naming)}
    carried = carried_paths((root / "pyproject.toml").read_text(encoding="utf-8"))
    selected, unread = select_tests(
        ["docs/reference/command-plane.md"], files, frozenset(files), carried
    )
    assert selected == {naming: "names", **dict.fromkeys(staging, "stages")}
    assert unread == []
