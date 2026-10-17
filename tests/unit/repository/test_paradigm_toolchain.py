"""The toolchain owner, its locked resolution and the common verbs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.toolchain import toolchain_gaps

if TYPE_CHECKING:
    from pathlib import Path

_MISE = ".config/mise/config.toml"
_LOCK = ".config/mise/mise.lock"
_LOCKED_TASKS = (
    '[settings]\nlocked = true\n\n[tasks.bootstrap]\nrun = "uv sync --locked"\n\n'
    '[tasks]\ncheck = "uv run nox -s check"\nfix = ["uv run nox -s fix"]\n'
)


def _gaps(root: Path, files: dict[str, str]) -> list[tuple[str, str]]:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    gaps = toolchain_gaps(load_repository_paradigm(), root, frozenset(files))
    return [(gap.required_gap, gap.repair) for gap in gaps]


def test_a_tracked_owner_missing_from_the_tree_is_unreadable(tmp_path: Path) -> None:
    """A tracked configuration that cannot be read is named, not taken as absent."""
    gaps = toolchain_gaps(load_repository_paradigm(), tmp_path, frozenset({_MISE, _LOCK}))
    assert [gap.required_gap for gap in gaps] == [f"repository_paradigm_toolchain_owner:{_MISE}"]


def test_a_locked_mise_owner_with_every_verb_conforms(tmp_path: Path) -> None:
    """Table and inline task forms both declare a verb."""
    files = {_MISE: _LOCKED_TASKS, _LOCK: "", "package.json": '{"scripts": {}}\n'}
    assert _gaps(tmp_path, files) == []


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        (
            {_MISE: _LOCKED_TASKS.replace('fix = ["uv run nox -s fix"]\n', ""), _LOCK: ""},
            [
                (
                    f"repository_paradigm_toolchain_verb:{_MISE}:tasks.fix",
                    f"add a fix task to {_MISE} that runs the native fix commands",
                )
            ],
        ),
        (
            {_MISE: _LOCKED_TASKS.replace("locked = true", "locked = false")},
            [
                (
                    f"repository_paradigm_toolchain_lock:{_MISE}:settings.locked",
                    f"set locked = true under [settings] in {_MISE}",
                ),
                (
                    f"repository_paradigm_toolchain_lock:{_LOCK}",
                    f"track {_LOCK}, written by mise lock",
                ),
            ],
        ),
        (
            {"package.json": '{"scripts": {"check": "node --test"}}\n'},
            [
                (
                    "repository_paradigm_toolchain_verb:package.json:scripts.bootstrap",
                    "add a bootstrap task to package.json that runs the native bootstrap commands",
                ),
                (
                    "repository_paradigm_toolchain_verb:package.json:scripts.fix",
                    "add a fix task to package.json that runs the native fix commands",
                ),
            ],
        ),
        (
            {"pyproject.toml": '[project]\nname = "sample"\n'},
            [
                (
                    f"repository_paradigm_toolchain_owner:{_MISE}",
                    (
                        f"add {_MISE} with locked resolution and bootstrap, check and fix tasks; "
                        "only mise and npm run tasks"
                    ),
                )
            ],
        ),
        (
            {_MISE: "[settings\n", _LOCK: ""},
            [(f"repository_paradigm_toolchain_owner:{_MISE}", f"make {_MISE} readable TOML")],
        ),
        (
            {"package.json": "{"},
            [
                (
                    "repository_paradigm_toolchain_owner:package.json",
                    "make package.json readable JSON",
                )
            ],
        ),
    ],
    ids=["missing-verb", "unlocked", "npm-owner", "uv-only", "unreadable", "unreadable-npm"],
)
def test_the_toolchain_owner_names_each_missing_part(
    tmp_path: Path, files: dict[str, str], expected: list[tuple[str, str]]
) -> None:
    """A tracked mise owns the verbs, npm owns them otherwise, and nothing else runs tasks."""
    assert _gaps(tmp_path, files) == expected
