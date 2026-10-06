"""Resolve concrete Python import targets and enforce semantic visibility."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.policy.layout.policy import module_name
from ethos.repository.policy.layout.policy import package_python_files
from ethos.repository.policy.layout.policy import semantic_python_files
from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.syntax import complete_python_tree

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
    """Consume the unique binding observation for static and dynamic imports."""
    sources = semantic_python_files(root, policy, files=files)
    modules = {module_name(root, path) for path in sources}
    findings: list[dict[str, object]] = []
    for path in sources:
        rel = path.relative_to(root).as_posix()
        consumer = module_name(root, path)
        package = consumer if path.name == "__init__.py" else consumer.rpartition(".")[0]
        source = path.read_text(encoding="utf-8")
        tree = complete_python_tree(source)
        if tree is None:
            findings.append({"gap": f"module_layout_import_unknown:{rel}", "path": rel})
            continue
        try:
            observed = PythonReferenceFlow(rel, {}).observe(tree, source=source)
        except (SyntaxError, ValueError):
            findings.append({"gap": f"module_layout_import_unknown:{rel}", "path": rel})
            continue
        findings.extend(
            {
                "gap": f"module_layout_private_import_unknown:{rel}:{item.line}"
                if item.state == "unknown"
                else "",
                **item.to_dict(),
            }
            for item in observed.uncertainties
            if item.kind == "import"
        )
        for site in observed.import_sites:
            target, symbol = site.module, site.name
            if f"{target}.{symbol}" in modules:
                target, symbol = f"{target}.{symbol}", ""
            violation = _private_boundary(target, package)
            if not violation and consumer != target and _private_name(symbol):
                violation = "symbol"
            if violation:
                findings.append(
                    {
                        "gap": f"module_layout_private_import:{rel}:{target}->{symbol}",
                        "path": rel,
                        "line": site.line,
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
