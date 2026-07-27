from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from ethos.normalization.coercion import string_list

POLICY_PATH = Path(".config/checks/module-layout/policy.toml")
DEFAULT_SEMANTIC_PATHS = (".agents/skills", "src/ethos", "tests", "tools")
DEFAULT_PACKAGE_PATHS = ("src/ethos",)


def load_policy(root: Path) -> dict[str, Any]:
    """Load module-layout policy with stable defaults."""
    path = root / POLICY_PATH
    if not path.exists():
        return {
            "semantic_paths": list(DEFAULT_SEMANTIC_PATHS),
            "package_paths": list(DEFAULT_PACKAGE_PATHS),
        }
    return tomllib.loads(path.read_text(encoding="utf-8"))


def semantic_python_files(
    root: Path,
    policy: dict[str, Any],
    *,
    files: tuple[Path, ...] | None = None,
) -> list[Path]:
    """Return every repository-owned Python carrier governed by semantic rules."""
    return _python_files(root, policy, "semantic_paths", DEFAULT_SEMANTIC_PATHS, files)


def package_python_files(
    root: Path,
    policy: dict[str, Any],
    *,
    files: tuple[Path, ...] | None = None,
) -> list[Path]:
    """Return product-package Python files governed by package-topology rules."""
    return _python_files(root, policy, "package_paths", DEFAULT_PACKAGE_PATHS, files)


def _python_files(
    root: Path,
    policy: dict[str, Any],
    key: str,
    defaults: tuple[str, ...],
    files: tuple[Path, ...] | None,
) -> list[Path]:
    configured_paths = string_list(policy.get(key)) or list(defaults)
    candidates = files if files is not None else tuple(root.rglob("*.py"))
    return sorted(
        {
            path
            for path in candidates
            if path.is_file()
            and "__pycache__" not in path.parts
            and _covered(path.relative_to(root), configured_paths)
        }
    )


def configured_semantic_paths(policy: dict[str, Any]) -> list[str]:
    """Return the fail-closed semantic carrier scope."""
    return string_list(policy.get("semantic_paths")) or list(DEFAULT_SEMANTIC_PATHS)


def configured_package_paths(policy: dict[str, Any]) -> list[str]:
    """Return the product-package topology scope."""
    return string_list(policy.get("package_paths")) or list(DEFAULT_PACKAGE_PATHS)


def _covered(relative: Path, configured_paths: list[str]) -> bool:
    return any(
        configured == "."
        or relative == Path(configured)
        or relative.is_relative_to(Path(configured))
        for configured in configured_paths
    )
