from __future__ import annotations

import ast
from typing import TYPE_CHECKING
from typing import Any

import ethos.repository.policy.layout.git.core as layout_git
from ethos.normalization.core import string_list
from ethos.repository.policy.layout.filesystem.core import DEFAULT_PATHS
from ethos.repository.policy.layout.filesystem.core import python_files

if TYPE_CHECKING:
    from pathlib import Path


def package_root_submodule_import_findings(
    root: Path,
    policy: dict[str, Any],
) -> list[dict[str, object]]:
    """Find `from package import submodule` imports that bypass concrete submodules."""
    module_names = _module_names(root, policy)
    findings: list[dict[str, object]] = []
    for path in python_files(root, policy):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level or not node.module:
                continue
            findings.extend(_package_root_imports(rel, node.module, node.names, module_names))
    return findings


def private_from_import_regression_findings(
    root: Path,
    policy: dict[str, Any],
) -> list[dict[str, object]]:
    """Find private-symbol from-imports in files changed from the layout reference."""
    changed = changed_python_files(root, policy)
    if not changed:
        return []
    findings: list[dict[str, object]] = []
    for path in python_files(root, policy):
        rel = path.relative_to(root).as_posix()
        if rel not in changed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level or not node.module:
                continue
            findings.extend(_private_from_imports(rel, node.module, node.names))
    return findings


def changed_python_files(root: Path, policy: dict[str, Any]) -> set[str]:
    """Return governed Python files changed from the layout reference."""
    current = {path.relative_to(root).as_posix() for path in python_files(root, policy)}
    paths = string_list(policy.get("paths")) or list(DEFAULT_PATHS)
    changed: set[str] = set()
    reference = layout_git.layout_reference(root)
    if reference is not None:
        output = layout_git.run_git(root, "diff", "--name-only", reference, "--", *paths)
        if output is not None:
            changed.update(output.splitlines())
    status = layout_git.run_git(root, "status", "--porcelain", "--", *paths)
    if status is not None:
        changed.update(_status_paths(status))
    return {rel for rel in changed if rel in current}


def _module_names(root: Path, policy: dict[str, Any]) -> set[str]:
    modules: set[str] = set()
    for path in python_files(root, policy):
        module = _module_name(root, path)
        if module:
            modules.add(module)
    return modules


def _module_name(root: Path, path: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = rel.parts
    if "src" in parts:
        parts = parts[parts.index("src") + 1 :]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _package_root_imports(
    rel: str,
    imported_from: str,
    aliases: list[ast.alias],
    module_names: set[str],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for alias in aliases:
        if alias.name == "*":
            continue
        if alias.asname and alias.asname.startswith("_"):
            continue
        module = f"{imported_from}.{alias.name}"
        if module not in module_names:
            continue
        gap = f"module_layout_package_root_submodule_import:{rel}:{module}"
        findings.append(
            {
                "gap": gap,
                "path": rel,
                "module": module,
                "imported_from": imported_from,
                "name": alias.name,
            }
        )
    return findings


def _private_from_imports(
    rel: str,
    imported_from: str,
    aliases: list[ast.alias],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for alias in aliases:
        if alias.name == "*":
            continue
        if not alias.name.startswith("_") or alias.name.startswith("__"):
            continue
        gap = f"module_layout_private_from_import:{rel}:{imported_from}->{alias.name}"
        findings.append(
            {
                "gap": gap,
                "path": rel,
                "module": imported_from,
                "name": alias.name,
            }
        )
    return findings


def _status_paths(status: str) -> set[str]:
    paths: set[str] = set()
    for line in status.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else ""
        if " -> " in path:
            _old, path = path.rsplit(" -> ", maxsplit=1)
        if path:
            paths.add(path)
    return paths
