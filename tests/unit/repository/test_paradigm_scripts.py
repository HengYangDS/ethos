"""Tracked shell and PowerShell scripts conform only as recorded official generator output."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.scripts import tracked_script_gaps

if TYPE_CHECKING:
    from pathlib import Path

_RECORD = ".config/mise/generated.toml"
_BOOTSTRAP = "#!/usr/bin/env bash\nset -eu\n# mise bootstrap\n"
_DIGEST = hashlib.sha256(_BOOTSTRAP.encode()).hexdigest()


def _record(generator: str = "mise-bootstrap", digest: str = _DIGEST) -> str:
    return (
        f'[[output]]\npath = "bin/mise"\ngenerator = "{generator}"\n'
        f'version = "2026.10.10"\nsha256 = "{digest}"\n'
    )


def _gaps(root: Path, files: dict[str, str]) -> list[tuple[str, str]]:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    gaps = tracked_script_gaps(load_repository_paradigm(), root, frozenset(files))
    return [(gap.required_gap, gap.repair) for gap in gaps]


@pytest.mark.parametrize(
    "files",
    [
        {"bin/mise": _BOOTSTRAP, _RECORD: _record()},
        {"bin/cli": "#!/usr/bin/env node\nconsole.log(1)\n", "README.md": "#!not a script\n"},
    ],
    ids=["recorded-generator-output", "other-interpreters"],
)
def test_recorded_generator_output_and_other_files_conform(
    tmp_path: Path, files: dict[str, str]
) -> None:
    """Official generator output with its version and digest is admitted."""
    assert _gaps(tmp_path, files) == []


_HAND_WRITTEN = (
    "replace {path} with native commands or toolchain-owner tasks; only the recorded output "
    "of a catalogued generator, such as `mise generate bootstrap`, may be tracked"
)
_REGENERATE = (
    "regenerate bin/mise with `mise generate bootstrap` and record its version and SHA-256 "
    f"in {_RECORD}"
)


@pytest.mark.parametrize(
    ("files", "carrier", "repair"),
    [
        ({"build.sh": "make all\n"}, "build.sh", _HAND_WRITTEN.format(path="build.sh")),
        (
            {"tools/run": "#!/usr/bin/env -S bash -eu\necho run\n"},
            "tools/run",
            _HAND_WRITTEN.format(path="tools/run"),
        ),
        (
            {"tools/setup.ps1": "Write-Output 1\n"},
            "tools/setup.ps1",
            _HAND_WRITTEN.format(path="tools/setup.ps1"),
        ),
        ({"bin/mise": _BOOTSTRAP, _RECORD: _record(digest="0" * 64)}, "bin/mise", _REGENERATE),
        (
            {"bin/mise": _BOOTSTRAP, _RECORD: _record(generator="hand-rolled")},
            "bin/mise",
            _HAND_WRITTEN.format(path="bin/mise"),
        ),
        (
            {"bin/mise": _BOOTSTRAP, _RECORD: "[[output]\n"},
            "bin/mise",
            _HAND_WRITTEN.format(path="bin/mise"),
        ),
    ],
    ids=[
        "hand-written",
        "interpreter-line",
        "powershell",
        "stale-digest",
        "unknown-generator",
        "unreadable-record",
    ],
)
def test_an_unadmitted_script_names_its_native_replacement(
    tmp_path: Path, files: dict[str, str], carrier: str, repair: str
) -> None:
    """A script outside a valid generator record is reported with its repair."""
    assert _gaps(tmp_path, files) == [(f"repository_paradigm_tracked_script:{carrier}", repair)]
