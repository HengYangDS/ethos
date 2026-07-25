from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from ethos.adapters.repo.git import git_stdout
from ethos.normalization.core import string_list

POLICY_PATH = Path(".config/checks/module-layout/policy.toml")
DEFAULT_SEMANTIC_PATHS = (".",)
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


def semantic_python_files(root: Path, policy: dict[str, Any]) -> list[Path]:
    """Return every repository-owned Python carrier governed by semantic rules."""
    return _python_files(root, policy, "semantic_paths", DEFAULT_SEMANTIC_PATHS)


def package_python_files(root: Path, policy: dict[str, Any]) -> list[Path]:
    """Return product-package Python files governed by package-topology rules."""
    return _python_files(root, policy, "package_paths", DEFAULT_PACKAGE_PATHS)


def _python_files(
    root: Path,
    policy: dict[str, Any],
    key: str,
    defaults: tuple[str, ...],
) -> list[Path]:
    configured_paths = string_list(policy.get(key)) or list(defaults)
    tracked = _tracked_python_files(root)
    if tracked is not None:
        return [path for path in tracked if _covered(path.relative_to(root), configured_paths)]
    files: list[Path] = []
    for configured in configured_paths:
        base = root / configured
        if base.is_file() and base.suffix == ".py":
            files.append(base)
        elif base.exists():
            files.extend(sorted(base.rglob("*.py")))
    return sorted({path for path in files if "__pycache__" not in path.parts})


def configured_semantic_paths(policy: dict[str, Any]) -> list[str]:
    """Return the fail-closed semantic carrier scope."""
    return string_list(policy.get("semantic_paths")) or list(DEFAULT_SEMANTIC_PATHS)


def configured_package_paths(policy: dict[str, Any]) -> list[str]:
    """Return the product-package topology scope."""
    return string_list(policy.get("package_paths")) or list(DEFAULT_PACKAGE_PATHS)


def _tracked_python_files(root: Path) -> list[Path] | None:
    output = git_stdout(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    if not output and not (root / ".git").exists():
        return None
    return sorted(
        path
        for relative in output.split("\0")
        if relative.endswith(".py") and (path := root / relative).is_file()
    )


def _covered(relative: Path, configured_paths: list[str]) -> bool:
    return any(
        configured == "."
        or relative == Path(configured)
        or relative.is_relative_to(Path(configured))
        for configured in configured_paths
    )
