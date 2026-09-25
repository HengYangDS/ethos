"""Identify source-code subjects before native quality evidence is selected."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

_LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".pyi": "python",
    ".go": "go",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
}

CARRIER_ROLES = frozenset(
    {"code", "test", "tooling", "docs", "config", "intent", "data", "generated", "snapshot"}
)


@dataclass(frozen=True, slots=True)
class CodeSubject:
    """One tracked source carrier with a language and behavioral role."""

    path: str
    language: str
    is_test: bool


def observed_code_subjects(
    repository_paths: tuple[str, ...],
    *,
    script_paths: tuple[str, ...] = (),
    roles: Mapping[str, str] | None = None,
) -> tuple[CodeSubject, ...]:
    """Flag known code carriers without treating a suffix as quality evidence."""
    subjects = []
    scripts = set(script_paths)
    declared = roles or {}
    for path in repository_paths:
        name = PurePosixPath(path).name
        role = declared.get(path)
        language = _LANGUAGE_BY_SUFFIX.get(PurePosixPath(path).suffix)
        if language is None and path in scripts:
            language = "script"
        if language is None and role in {"code", "test", "tooling"}:
            language = "unqualified"
        if language is None:
            continue
        is_test = (
            role == "test"
            or path.startswith(("tests/", "test/"))
            or name.startswith("test_")
            or name.endswith(("_test.go", ".test.js", ".test.mjs", ".test.cjs"))
        )
        subjects.append(CodeSubject(path, language, is_test))
    return tuple(sorted(subjects, key=lambda subject: subject.path))
