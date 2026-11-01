"""A tracked license grant is a recognized standard text, linked and consistently declared."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

from ethos.contracts.paradigm.declaration import license_template
from tests.support.paradigm import CONFORMING
from tests.support.paradigm import LINKED_README
from tests.support.paradigm import MIT_GRANT
from tests.support.paradigm import paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

_MARKUP = re.compile(r'<<(?:beginOptional|endOptional|var;(?:[^"]|"[^"]*")*?)>>')


def _published(identifier: str) -> str:
    """Render a recognized SPDX template with each replaceable field in its original text."""

    def original(markup: re.Match[str]) -> str:
        return dict(re.findall(r'(\w+)="([^"]*)"', markup.group(0))).get("original", "")

    return _MARKUP.sub(original, license_template(identifier))


_APACHE = _published("Apache-2.0")
_PLACEHOLDER = MIT_GRANT.replace("2026 Sample Authors", "<year> <copyright holders>")
_PROPRIETARY = "Sample Proprietary License\n\nCopyright (c) 2026 Sample Authors.\n"
_PROPRIETARY_PROJECT = CONFORMING["pyproject.toml"] + 'license = "LicenseRef-Proprietary"\n'


def _package(license_value: object) -> str:
    return json.dumps({"scripts": {"check": "node check.mjs"}, "license": license_value}) + "\n"


def _lock(license_value: object) -> str:
    return json.dumps({"lockfileVersion": 3, "packages": {"": {"license": license_value}}}) + "\n"


_CASES = {
    "mit-declared": (
        {
            "LICENSE": MIT_GRANT,
            "README.md": LINKED_README,
            "package.json": _package("MIT"),
            "package-lock.json": _lock("MIT"),
        },
        [],
    ),
    "apache-appendix": (
        {
            "LICENSE": _APACHE.replace(
                "[yyyy] [name of copyright owner]", "2026 Sample Authors"
            ).replace("http://", "https://"),
            "README.md": LINKED_README.replace("MIT", "Apache"),
        },
        [],
    ),
    "apache-unfilled-appendix": (
        {"LICENSE": _APACHE, "README.md": "[license](./LICENSE#terms)\n"},
        [],
    ),
    "no-grant": ({}, []),
    "untitled": (
        {"LICENSE": MIT_GRANT.removeprefix("MIT License\n\n"), "README.md": LINKED_README},
        [],
    ),
    "retitled": (
        {
            "LICENSE": MIT_GRANT.replace("MIT License", "Apache License", 1),
            "README.md": LINKED_README,
        },
        ["license_grant:LICENSE"],
    ),
    "edited": (
        {"LICENSE": MIT_GRANT.replace("free of charge", "for a fee"), "README.md": LINKED_README},
        ["license_grant:LICENSE"],
    ),
    "unnamed-holder": (
        {"LICENSE": _PLACEHOLDER, "README.md": LINKED_README},
        ["license_grant:LICENSE"],
    ),
    "unlinked": ({"LICENSE": MIT_GRANT}, ["license_entry:README.md"]),
    "metadata-disagrees": (
        {
            "LICENSE": MIT_GRANT,
            "README.md": LINKED_README,
            "package.json": _package("Apache-2.0"),
            "package-lock.json": _lock(1),
            "pyproject.toml": CONFORMING["pyproject.toml"] + 'license = "MIT"\n',
        },
        ["license_metadata:package.json", "license_metadata:package-lock.json"],
    ),
    "declared-without-grant": ({"package.json": _package("MIT")}, ["license_grant:LICENSE"]),
    "private-unlicensed": ({"package.json": _package("UNLICENSED")}, []),
    "proprietary-declared": (
        {
            "LICENSE": _PROPRIETARY,
            "README.md": LINKED_README,
            "package.json": _package("MIT"),
            "pyproject.toml": _PROPRIETARY_PROJECT,
        },
        ["license_metadata:package.json"],
    ),
    "proprietary-undeclared": (
        {"LICENSE": _PROPRIETARY, "README.md": LINKED_README},
        ["license_grant:LICENSE"],
    ),
}


@pytest.mark.parametrize(("changes", "gaps"), _CASES.values(), ids=_CASES)
def test_license_grant_is_standard_linked_and_consistently_declared(
    tmp_path: Path, changes: dict[str, str], gaps: list[str]
) -> None:
    """The repository's own license is judged; its choice of license is its own."""
    report = paradigm_report(tmp_path, {**CONFORMING, **changes})
    assert report["required_gaps"] == [f"repository_paradigm_{gap}" for gap in gaps]


@pytest.mark.parametrize(
    ("holder", "accepted"),
    [
        ("", False),
        ("2026", False),
        ("2026 <copyright holders>", False),
        ("2026 Sample Authors", True),
        ("2020-2026 李明", True),
        ("Example Foundation", True),
    ],
)
def test_documentation_license_names_a_holder_without_package_metadata(
    tmp_path: Path, holder: str, *, accepted: bool
) -> None:
    """A year or an unresolved template is not a holder; a grant needs no package."""
    report = paradigm_report(
        tmp_path,
        {"LICENSE": MIT_GRANT.replace("2026 Sample Authors", holder), "README.md": LINKED_README},
    )
    grants = [gap for gap in report["required_gaps"] if "license_grant" in gap]
    assert grants == ([] if accepted else ["repository_paradigm_license_grant:LICENSE"])
