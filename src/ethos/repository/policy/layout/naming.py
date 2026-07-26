from __future__ import annotations

import ast
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.measure import effective_code_lines
from ethos.repository.policy.layout.policy import semantic_python_files

if TYPE_CHECKING:
    from pathlib import Path


DEFAULT_AMBIGUOUS_MODULE_NAMES = frozenset(
    {
        "base",
        "common",
        "core",
        "helpers",
        "manager",
        "misc",
        "service",
        "shared",
        "utils",
    }
)
_ROLE_KEYS = frozenset(
    {
        "path",
        "role",
        "concept",
        "authority_refs",
        "public_symbols",
        "max_eloc",
        "allowed_import_roots",
    }
)
_ROLES = frozenset({"kernel", "report_aggregator"})


def ambiguous_module_findings(
    root: Path,
    policy: dict[str, Any],
    files: tuple[Path, ...] | None = None,
) -> list[dict[str, object]]:
    """Find ambiguous module names lacking an exact closed role contract."""
    names = {
        str(name)
        for name in policy.get("ambiguous_module_names", DEFAULT_AMBIGUOUS_MODULE_NAMES)
        if isinstance(name, str) and name
    }
    roles = _ambiguous_module_roles(root, policy)
    findings: list[dict[str, object]] = []
    for path in semantic_python_files(root, policy, files=files):
        module = path.stem.lstrip("_")
        if module not in names:
            continue
        relative = path.relative_to(root).as_posix()
        role = roles.get(relative)
        reasons = _role_reasons(path, role)
        if not reasons:
            continue
        findings.append(
            {
                "gap": f"module_layout_ambiguous_module_role:{relative}:{','.join(reasons)}",
                "path": relative,
                "module": module,
                "reasons": reasons,
            }
        )
    return findings


def ambiguous_package_findings(
    root: Path,
    policy: dict[str, Any],
    files: tuple[Path, ...] | None = None,
) -> list[dict[str, object]]:
    """Find generic package-directory names that conceal semantic ownership."""
    names = {
        str(name)
        for name in policy.get("ambiguous_module_names", DEFAULT_AMBIGUOUS_MODULE_NAMES)
        if isinstance(name, str) and name
    }
    directories = {
        parent
        for path in semantic_python_files(root, policy, files=files)
        for parent in path.parents
        if parent != root and root in parent.parents
    }
    return [
        {
            "gap": f"module_layout_ambiguous_package:{directory.relative_to(root).as_posix()}",
            "path": directory.relative_to(root).as_posix(),
            "package": directory.name.lstrip("_"),
        }
        for directory in sorted(directories)
        if directory.name.lstrip("_") in names
    ]


def surface_core_command_findings(
    root: Path,
    policy: dict[str, Any],
    files: tuple[Path, ...] | None = None,
) -> list[dict[str, object]]:
    """Reject command definitions and declaration targets in CLI ``core.py`` files."""
    findings: list[dict[str, object]] = []
    for path in semantic_python_files(root, policy, files=files):
        relative = path.relative_to(root).as_posix()
        if path.name != "core.py" or "/surface/cli/" not in f"/{relative}":
            continue
        source = path.read_text(encoding="utf-8")
        if ".command(" not in source:
            continue
        findings.append(
            {
                "gap": f"module_layout_surface_core_command:{relative}",
                "path": relative,
            }
        )
    return findings


def multiple_command_owner_findings(
    root: Path,
    policy: dict[str, Any],
    files: tuple[Path, ...] | None = None,
) -> list[dict[str, object]]:
    """Reject a module that registers commands on multiple Cyclopts apps."""
    findings: list[dict[str, object]] = []
    for path in semantic_python_files(root, policy, files=files):
        relative = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        owners = {
            owner
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            for decorator in node.decorator_list
            if (owner := _command_owner(decorator))
        }
        if len(owners) <= 1:
            continue
        findings.append(
            {
                "gap": (
                    f"module_layout_multiple_command_owners:{relative}:{','.join(sorted(owners))}"
                ),
                "path": relative,
                "owners": sorted(owners),
            }
        )
    return findings


def _ambiguous_module_roles(root: Path, policy: dict[str, Any]) -> dict[str, dict[str, object]]:
    roles: dict[str, dict[str, object]] = {}
    value = policy.get("ambiguous_module_roles", [])
    if not isinstance(value, list):
        return roles
    for item in value:
        if not isinstance(item, dict) or set(item) != _ROLE_KEYS:
            continue
        path = item.get("path")
        if not isinstance(path, str) or not path or "*" in path or (root / path).is_dir():
            continue
        roles[path] = item
    return roles


def _role_reasons(path: Path, role: dict[str, object] | None) -> list[str]:
    if role is None:
        return ["contract_missing"]
    reasons: list[str] = []
    if role.get("role") not in _ROLES:
        reasons.append("role_invalid")
    if not isinstance(role.get("concept"), str) or not str(role["concept"]).strip():
        reasons.append("concept_missing")
    reasons.extend(_role_list_reasons(role))
    maximum = role.get("max_eloc")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
        reasons.append("max_eloc_invalid")
    elif effective_code_lines(path) > maximum:
        reasons.append("size_exceeded")
    if not reasons:
        public = sorted(_public_definitions(path))
        public_symbols = cast("list[str]", role["public_symbols"])
        if public != sorted(public_symbols):
            reasons.append("public_drift")
        allowed = tuple(cast("list[str]", role["allowed_import_roots"]))
        if any(not module.startswith(allowed) for module in _imported_modules(path)):
            reasons.append("import_drift")
    return reasons


def _role_list_reasons(role: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    for field in ("public_symbols", "allowed_import_roots"):
        value = role.get(field)
        valid = isinstance(value, list) and all(isinstance(item, str) for item in value)
        if not valid:
            reasons.append(f"{field}_invalid")
    authority_refs = role.get("authority_refs")
    if not (
        isinstance(authority_refs, list)
        and bool(authority_refs)
        and all(isinstance(item, str) for item in authority_refs)
    ):
        reasons.append("authority_refs_invalid")
    return reasons


def _public_definitions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        and not node.name.startswith("_")
    }


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        module
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for module in (
            (alias.name for alias in node.names)
            if isinstance(node, ast.Import)
            else ((node.module or ""),)
        )
        if module
    }


def _command_owner(decorator: ast.expr) -> str:
    call = decorator if isinstance(decorator, ast.Call) else None
    target = call.func if call else decorator
    if not isinstance(target, ast.Attribute) or target.attr != "command":
        return ""
    return target.value.id if isinstance(target.value, ast.Name) else ""
