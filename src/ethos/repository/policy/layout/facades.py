"""Detect alias facades and compatibility shells without owned behavior."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.policy.layout.imports import module_bindings
from ethos.repository.policy.layout.policy import module_name
from ethos.repository.policy.layout.policy import semantic_python_files

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def private_alias_findings(
    root: Path,
    policy: dict[str, Any],
    files: tuple[Path, ...] | None = None,
) -> list[dict[str, object]]:
    """Find imports renamed to private aliases or away from their canonical names."""
    sources = semantic_python_files(root, policy, files=files)
    modules = {module_name(root, path) for path in sources}
    findings: list[dict[str, object]] = []
    for path in sources:
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        defined, imported = module_bindings(root, path)
        bound = {*defined, *imported}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                findings.extend(_import_private_aliases(rel, node.names))
            elif isinstance(node, ast.ImportFrom) and node.module:
                findings.extend(_from_import_aliases(rel, node, bound, modules))
    return findings


def facade_findings(
    root: Path,
    policy: dict[str, Any],
    files: tuple[Path, ...] | None = None,
) -> dict[str, list[dict[str, object]]]:
    """Find runtime package initializers, import-only modules and `__getattr__` export shells.

    Each selected file is parsed once. A package `__init__.py` is judged as an initializer, any
    other module as an import facade and a dynamic-export shell.
    """
    kinds: dict[str, tuple[bool, Callable[[ast.Module], list[str]]]] = {
        "package_init_facade": (True, package_init_facade_reasons),
        "module_facade": (False, module_facade_reasons),
        "dynamic_compat_facade": (False, dynamic_compat_facade_reasons),
    }
    findings: dict[str, list[dict[str, object]]] = {f"{kind}_findings": [] for kind in kinds}
    for path in semantic_python_files(root, policy, files=files):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for kind, (initializer, reasons) in kinds.items():
            if (path.name == "__init__.py") == initializer and (found := reasons(tree)):
                gap = f"module_layout_{kind}:{rel}"
                findings[f"{kind}_findings"].append({"gap": gap, "path": rel, "reasons": found})
    return findings


def dynamic_compat_facade_reasons(tree: ast.Module) -> list[str]:
    """Return reasons a module-level `__getattr__` acts as a compatibility shell."""
    reasons: list[str] = []
    for node in _body_without_docstring(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name == "__getattr__":
            _append_reason(reasons, "dynamic_export")
            if any(isinstance(inner, (ast.Import, ast.ImportFrom)) for inner in ast.walk(node)):
                _append_reason(reasons, "lazy_import")
    return reasons


def package_init_facade_reasons(tree: ast.Module) -> list[str]:
    """Return reasons an `__init__.py` is not declaration-only."""
    reasons: list[str] = []
    body = _body_without_docstring(tree)
    for node in body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            _append_reason(reasons, "import")
        elif not isinstance(node, ast.Pass):
            _append_reason(reasons, "runtime_code")
    return reasons


def module_facade_reasons(tree: ast.Module) -> list[str]:
    """Return reasons an ordinary module is only an import facade."""
    body = _body_without_docstring(tree)
    import_only = False
    runtime_code = False
    for node in body:
        if _is_future_import(node):
            continue
        if _is_non_future_import(node) or _is_type_checking_import_block(node):
            import_only = True
        elif _is_all_assignment(node):
            continue
        elif not isinstance(node, ast.Pass):
            runtime_code = True
    if runtime_code or not import_only:
        return []
    return ["import_only"]


def _body_without_docstring(tree: ast.Module) -> list[ast.stmt]:
    body = list(tree.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _is_future_import(node: ast.AST) -> bool:
    return isinstance(node, ast.ImportFrom) and node.module == "__future__"


def _is_non_future_import(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return True
    return isinstance(node, ast.ImportFrom) and node.module != "__future__"


def _is_type_checking_import_block(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False
    if not isinstance(node.test, ast.Name) or node.test.id != "TYPE_CHECKING":
        return False
    return all(isinstance(item, (ast.Import, ast.ImportFrom, ast.Pass)) for item in node.body)


def _is_all_assignment(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "__all__"
    )


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _import_private_aliases(rel: str, aliases: list[ast.alias]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for alias in aliases:
        if alias.asname and alias.asname.startswith("_"):
            gap = f"module_layout_private_import_alias:{rel}:{alias.name}->{alias.asname}"
            findings.append({"gap": gap, "path": rel, "source": alias.name, "alias": alias.asname})
    return findings


def _from_import_aliases(
    rel: str,
    node: ast.ImportFrom,
    bound: set[str],
    modules: set[str],
) -> list[dict[str, object]]:
    """Admit a public rename only for a name the module binds or a module namespace."""
    findings: list[dict[str, object]] = []
    for alias in node.names:
        source = f"{node.module}.{alias.name}"
        renamed = alias.asname not in {None, alias.name} and alias.name not in bound
        if alias.asname and alias.asname.startswith("_"):
            kind = "private_import_alias"
        elif renamed and source not in modules:
            kind = "import_rename"
        else:
            continue
        findings.append(
            {
                "gap": f"module_layout_{kind}:{rel}:{source}->{alias.asname}",
                "path": rel,
                "line": node.lineno,
                "module": node.module,
                "source": source,
                "alias": alias.asname,
            }
        )
    return findings
