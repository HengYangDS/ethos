"""Tracked scripts of the repository paradigm.

A file is a script when its suffix or its interpreter line names a shell or PowerShell.
It conforms only as the output that a catalogued official generator recorded with its
version and SHA-256, so every other script is replaced by native commands or tasks.
"""

from __future__ import annotations

import hashlib
import posixpath
import tomllib
from typing import TYPE_CHECKING

from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm
    from ethos.contracts.paradigm.declaration import ScriptGenerator

_INTERPRETER_LINE_BYTES = 256


def tracked_script_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Report each tracked script that no catalogued generator recorded exactly."""
    records = _recorded_outputs(paradigm, root, tracked)
    for path in sorted(entry for entry in tracked if is_script(paradigm, root, entry)):
        recorded = records.get(path)
        if recorded is None:
            yield ParadigmGap(
                "tracked-script",
                path,
                f"replace {path} with native commands or toolchain-owner tasks; only the "
                "recorded output of a catalogued generator, such as `mise generate bootstrap`, "
                "may be tracked",
            )
            continue
        generator, digest = recorded
        if _digest(root, path) != digest:
            yield ParadigmGap(
                "tracked-script",
                path,
                f"regenerate {path} with `{generator.command}` and record its version and "
                f"SHA-256 in {generator.record}",
            )


def _recorded_outputs(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> dict[str, tuple[ScriptGenerator, str]]:
    """Map each output recorded by its own catalogued generator to that generator and digest."""
    recorded: dict[str, tuple[ScriptGenerator, str]] = {}
    for generator in paradigm.scripts.generator:
        try:
            declared = tomllib.loads(tracked_text(root, generator.record, tracked) or "")
        except tomllib.TOMLDecodeError:
            continue
        outputs = declared.get("output")
        for output in outputs if isinstance(outputs, list) else ():
            if (
                isinstance(output, dict)
                and output.get("generator") == generator.id
                and isinstance(output.get("path"), str)
                and isinstance(output.get("version"), str)
                and output["version"]
                and isinstance(output.get("sha256"), str)
            ):
                recorded[output["path"]] = (generator, output["sha256"])
    return recorded


def is_script(paradigm: RepositoryParadigm, root: Path, path: str) -> bool:
    """Recognize a script by its suffix or by the interpreter its first line names."""
    if path.endswith(paradigm.scripts.suffixes):
        return True
    try:
        with (root / path).open("rb") as carrier:
            opening = carrier.read(_INTERPRETER_LINE_BYTES)
    except OSError:
        return False
    if not opening.startswith(b"#!"):
        return False
    words = opening[2:].split(b"\n", 1)[0].decode("utf-8", errors="replace").split()
    if words and posixpath.basename(words[0]) == "env":
        words = [word for word in words[1:] if not word.startswith("-")]
    return bool(words) and posixpath.basename(words[0]) in paradigm.scripts.interpreters


def _digest(root: Path, path: str) -> str:
    try:
        return hashlib.sha256((root / path).read_bytes()).hexdigest()
    except OSError:
        return ""
