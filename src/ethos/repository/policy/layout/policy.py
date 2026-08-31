from __future__ import annotations

import ast
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


def empty_package_findings(
    root: Path,
    policy: dict[str, Any],
    files: tuple[Path, ...] | None = None,
) -> list[dict[str, object]]:
    """Find declaration-only leaf packages with no observed public import boundary."""
    package_files = package_python_files(root, policy, files=files)
    semantic_files = semantic_python_files(root, policy, files=files)
    imported_modules = _imported_modules(semantic_files)
    findings: list[dict[str, object]] = []
    for init in package_files:
        if init.name != "__init__.py":
            continue
        package = init.parent
        if any(path.parent == package and path.name != "__init__.py" for path in package_files):
            continue
        if any(path.is_dir() and path.name != "__pycache__" for path in package.iterdir()):
            continue
        if any(path.is_file() and path.suffix != ".py" for path in package.iterdir()):
            continue
        module = _module_name(root, init)
        if module in imported_modules:
            continue
        relative = package.relative_to(root).as_posix()
        findings.append(
            {
                "gap": f"module_layout_empty_package:{relative}",
                "path": relative,
                "module": module,
            }
        )
    return findings


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


def _module_name(root: Path, path: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = relative.parts
    if "src" in parts:
        parts = parts[parts.index("src") + 1 :]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _imported_modules(files: list[Path]) -> set[str]:
    imported: set[str] = set()
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    return imported
