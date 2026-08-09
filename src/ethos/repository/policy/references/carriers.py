"""Declare repository carriers for reference observation and ownership."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ReferenceCarrier:
    """One native syntax carrier and its policy roles."""

    name: str
    filenames: frozenset[str] = frozenset()
    suffixes: frozenset[str] = frozenset()
    declarations: tuple[str, ...] = ()
    path_declarations: tuple[tuple[str, str], ...] = ()
    entrypoints: tuple[str, ...] = ()
    entrypoint_globs: tuple[str, ...] = ()

    def matches(self, path: str) -> bool:
        """Return whether this carrier owns the path syntax."""
        pure = PurePosixPath(path)
        return pure.name in self.filenames or pure.suffix.lower() in self.suffixes

    def declaration_kinds(self, path: str) -> tuple[str, ...]:
        """Return native declarations owned by this carrier path."""
        exact = tuple(
            kind for declared_path, kind in self.path_declarations if path == declared_path
        )
        return (*self.declarations, *exact)


REFERENCE_CARRIERS = (
    ReferenceCarrier(
        "pyproject",
        filenames=frozenset({"pyproject.toml"}),
        declarations=("python-project",),
        entrypoints=("pyproject.toml",),
    ),
    ReferenceCarrier(
        "package-json",
        filenames=frozenset({"package.json"}),
        declarations=("node-package",),
        entrypoints=("package.json",),
    ),
    ReferenceCarrier(
        "python",
        suffixes=frozenset({".py"}),
        declarations=("commands",),
        entrypoints=(
            "tools/ci/ci_templates.py",
            "tools/ci/architecture_projection.py",
            "tools/ci/python_test_gate.py",
        ),
    ),
    ReferenceCarrier(
        "yaml",
        suffixes=frozenset({".yaml", ".yml"}),
        entrypoints=(".gitlab-ci.yml",),
        entrypoint_globs=(
            ".github/workflows/*.yml",
            ".github/workflows/*.yaml",
            ".config/ci/**/*.yml",
            ".config/ci/**/*.yaml",
        ),
    ),
    ReferenceCarrier(
        "shell",
        suffixes=frozenset({".sh"}),
        entrypoint_globs=("tools/ci/scripts/*",),
    ),
    ReferenceCarrier("markdown", suffixes=frozenset({".md"})),
    ReferenceCarrier(
        "text",
        suffixes=frozenset({".json", ".mjs", ".toml"}),
        path_declarations=(
            (".config/checks/deptry/policy.toml", "python-import-policy"),
            ("system/gates.toml", "gates"),
            ("system/tools.toml", "tools"),
            (".ethos/profile.toml", "profile"),
            ("system/surfaces.toml", "surfaces"),
            (".ethos/release.toml", "release"),
            (".config/checks/ci/templates.toml", "providers"),
        ),
        entrypoints=("system/tools.toml", ".config/checks/pytest/pytest.ini"),
        entrypoint_globs=(".config/ci/**/*.toml",),
    ),
)

REFERENCE_KINDS = ("import", "distribution", "executable", "reference", "command", "value")
REFERENCE_SCAN_ROOTS = (".agents/skills", "src/ethos", "tests", "tools")


def reference_carrier(path: str) -> ReferenceCarrier:
    """Resolve a supported path through the single ordered carrier table."""
    for carrier in REFERENCE_CARRIERS:
        if carrier.matches(path):
            return carrier
    message = f"unsupported reference carrier: {path}"
    raise ValueError(message)


def reference_paths(root: Path, declared: Iterable[Path]) -> list[Path]:
    """Return active files whose syntax has a declared reference carrier."""
    paths = {path for path in declared if _is_reference_path(root, path)}
    for relative in REFERENCE_SCAN_ROOTS:
        base = root / relative
        if not base.exists():
            continue
        paths.update(
            path
            for path in base.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and _is_reference_path(root, path)
        )
    return sorted(paths)


def entrypoint_files(root: Path) -> list[tuple[str, Path]]:
    """Return generated-state entrypoints declared by native carriers."""
    candidates: dict[str, Path] = {}
    for carrier in REFERENCE_CARRIERS:
        for relative in carrier.entrypoints:
            path = root / relative
            if path.is_file():
                candidates[relative] = path
        for pattern in carrier.entrypoint_globs:
            candidates.update(
                (path.relative_to(root).as_posix(), path)
                for path in root.glob(pattern)
                if path.is_file()
            )
    return sorted(candidates.items())


def declaration_files(files: dict[str, str], declaration: str) -> dict[str, str]:
    """Return files selected by the one native declaration table."""
    return {
        path: text
        for path, text in files.items()
        if declaration in reference_carrier(path).declaration_kinds(path)
    }


def _is_reference_path(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return False
    return any(carrier.matches(relative) for carrier in REFERENCE_CARRIERS)
