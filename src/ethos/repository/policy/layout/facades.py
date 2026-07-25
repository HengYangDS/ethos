from __future__ import annotations

import ast
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.policy.layout.policy import semantic_python_files

if TYPE_CHECKING:
    from pathlib import Path


def private_alias_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find imports renamed to private compatibility aliases."""
    findings: list[dict[str, object]] = []
    for path in semantic_python_files(root, policy):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                findings.extend(_import_private_aliases(rel, node.names))
            elif isinstance(node, ast.ImportFrom) and node.module:
                findings.extend(_from_import_private_aliases(rel, node.module, node.names))
    return findings


def package_init_facade_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find package `__init__.py` files that act as runtime facades."""
    findings: list[dict[str, object]] = []
    for path in semantic_python_files(root, policy):
        if path.name != "__init__.py":
            continue
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        reasons = package_init_facade_reasons(tree)
        if not reasons:
            continue
        gap = f"module_layout_package_init_facade:{rel}"
        findings.append({"gap": gap, "path": rel, "reasons": reasons})
    return findings


def module_facade_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find ordinary modules that only re-export imported symbols."""
    findings: list[dict[str, object]] = []
    for path in semantic_python_files(root, policy):
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        reasons = module_facade_reasons(tree)
        if not reasons:
            continue
        gap = f"module_layout_module_facade:{rel}"
        findings.append({"gap": gap, "path": rel, "reasons": reasons})
    return findings


def dynamic_compat_facade_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find modules that hide compatibility exports behind module `__getattr__`."""
    findings: list[dict[str, object]] = []
    for path in semantic_python_files(root, policy):
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        reasons = dynamic_compat_facade_reasons(tree)
        if not reasons:
            continue
        gap = f"module_layout_dynamic_compat_facade:{rel}"
        findings.append({"gap": gap, "path": rel, "reasons": reasons})
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


def _from_import_private_aliases(
    rel: str,
    module: str,
    aliases: list[ast.alias],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for alias in aliases:
        if not alias.asname or not alias.asname.startswith("_"):
            continue
        source = f"{module}.{alias.name}"
        gap = f"module_layout_private_import_alias:{rel}:{source}->{alias.asname}"
        findings.append({"gap": gap, "path": rel, "source": source, "alias": alias.asname})
    return findings
