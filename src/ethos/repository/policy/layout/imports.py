"""Resolve concrete Python import targets and enforce semantic visibility."""

from __future__ import annotations

import ast
from importlib.util import resolve_name
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.policy.layout.policy import module_name
from ethos.repository.policy.layout.policy import package_python_files
from ethos.repository.policy.layout.policy import semantic_python_files

if TYPE_CHECKING:
    from pathlib import Path


def package_root_submodule_import_findings(
    root: Path,
    policy: dict[str, Any],
    files: tuple[Path, ...] | None = None,
) -> list[dict[str, object]]:
    """Find `from package import submodule` imports that bypass concrete submodules."""
    module_names = _module_names(root, policy, files)
    findings: list[dict[str, object]] = []
    for path in semantic_python_files(root, policy, files=files):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level or not node.module:
                continue
            findings.extend(_package_root_imports(rel, node.module, node.names, module_names))
    return findings


def private_import_findings(
    root: Path,
    policy: dict[str, Any],
    files: tuple[Path, ...] | None = None,
) -> list[dict[str, object]]:
    """Check module and symbol visibility for every governed Python consumer."""
    sources = semantic_python_files(root, policy, files=files)
    modules = {module_name(root, path) for path in sources}
    findings: list[dict[str, object]] = []
    for path in sources:
        rel = path.relative_to(root).as_posix()
        consumer = module_name(root, path)
        package = consumer if path.name == "__init__.py" else consumer.rpartition(".")[0]
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets = ((alias.name, "") for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                try:
                    origin = resolve_name("." * node.level + (node.module or ""), package)
                except (ImportError, ValueError):
                    findings.append({"gap": f"module_layout_import_unresolved:{rel}:{node.lineno}"})
                    continue
                targets = (
                    (f"{origin}.{alias.name}", "")
                    if f"{origin}.{alias.name}" in modules
                    else (origin, alias.name)
                    for alias in node.names
                )
            else:
                continue
            for target, symbol in targets:
                violation = _private_boundary(target, package)
                if not violation and consumer != target and _private_name(symbol):
                    violation = "symbol"
                if violation:
                    findings.append(
                        {
                            "gap": f"module_layout_private_import:{rel}:{target}->{symbol}",
                            "path": rel,
                            "line": node.lineno,
                            "module": target,
                            "name": symbol,
                            "consumer": consumer,
                            "boundary": violation,
                        }
                    )
    return findings


def _private_name(name: str) -> bool:
    """Keep protocol dunders distinct from private implementation names."""
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def _private_boundary(module: str, consumer_package: str) -> str:
    """Private modules admit direct siblings; private packages admit their own subtree."""
    parts = tuple(module.split("."))
    consumer = tuple(consumer_package.split("."))
    for index, part in enumerate(parts):
        if not _private_name(part):
            continue
        owner = parts[:index]
        private_scope = parts[: index + 1]
        if consumer != owner and consumer[: len(private_scope)] != private_scope:
            return "module"
    return ""


def _module_names(
    root: Path,
    policy: dict[str, Any],
    files: tuple[Path, ...] | None,
) -> set[str]:
    return {
        module
        for path in package_python_files(root, policy, files=files)
        if (module := module_name(root, path))
    }


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
