"""Enumerate a repository's product surface: the active text files that policy reads."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

PRODUCT_SURFACES = (
    "AGENTS.md",
    "CHANGELOG.md",
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "package.json",
    "package-lock.json",
    "pyproject.toml",
    "uv.lock",
    ".config",
    ".github",
    ".gitignore",
    ".gitlab",
    ".gitlab-ci.yml",
    "assets",
    "packages",
    "distributions",
    ".ethos",
    ".agents/skills",
    "docs/README.md",
    "docs/_meta",
    "docs/architecture",
    "docs/concepts",
    "docs/decisions",
    "docs/governance",
    "docs/reference",
    "docs/plans",
    "docs/guides",
    "openspec/README.md",
    "openspec/config.yaml",
    "openspec/specs",
    "rules",
    "system",
    "tests",
    "tools",
)
HISTORICAL_SURFACE_PREFIXES = (
    "openspec/changes/archive/",
    "docs/history/",
)
RELEASE_VISIBLE_HISTORICAL_SURFACE_PREFIXES = HISTORICAL_SURFACE_PREFIXES
SKIPPED_PRODUCT_DIR_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "node_modules",
}
TEXT_SUFFIXES = {
    ".c4",
    ".Dockerfile",
    ".dockerfile",
    ".ini",
    ".json",
    ".lock",
    ".md",
    ".mjs",
    ".mmd",
    ".py",
    ".sh",
    ".svg",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_FILENAMES = {
    ".gitignore",
    ".shellcheckrc",
    "Containerfile",
    "Dockerfile",
    "LICENSE",
    "pre-commit",
    "pre-push",
    "reference-transaction",
}


def declared_product_surface_roots(root: Path) -> tuple[str, ...]:
    """Return policy roots plus carriers declared by the product surface contract."""
    path = root / "system/surfaces.toml"
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        payload = {}
    declared = payload.get("surface", [])
    carriers = (
        str(surface.get("carrier", "")).strip("/")
        for surface in declared
        if isinstance(surface, dict)
    )
    active = (*PRODUCT_SURFACES, *carriers, "openspec/changes")
    return tuple(dict.fromkeys(surface for surface in active if surface))


def _is_text_product_file(path: Path, *, root: Path, surfaces: tuple[str, ...]) -> bool:
    rel = path.relative_to(root).as_posix()
    if any(rel.startswith(prefix) for prefix in HISTORICAL_SURFACE_PREFIXES):
        return False
    if any(part in SKIPPED_PRODUCT_DIR_PARTS for part in path.relative_to(root).parts):
        return False
    if not (path.is_file() and (path.suffix in TEXT_SUFFIXES or path.name in TEXT_FILENAMES)):
        return False
    return any(rel == surface or rel.startswith(f"{surface}/") for surface in surfaces)


def product_surface_files(root: Path) -> list[Path]:
    """Return active text files from every policy and declared product surface."""
    files: list[Path] = []
    surfaces = declared_product_surface_roots(root)
    for surface in surfaces:
        base = root / surface
        if base.is_file() and _is_text_product_file(base, root=root, surfaces=surfaces):
            files.append(base)
        elif base.is_dir():
            files.extend(
                path
                for path in base.rglob("*")
                if _is_text_product_file(path, root=root, surfaces=surfaces)
            )
    return sorted(set(files))
