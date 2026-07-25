from __future__ import annotations

import ast
from collections import defaultdict
from typing import TYPE_CHECKING
from typing import Any

from ethos.measure import effective_code_lines
from ethos.repository.policy.layout.filesystem.core import DEFAULT_FLAT_DIRECTORY_LIMIT
from ethos.repository.policy.layout.filesystem.core import DEFAULT_SUFFIX_GROUP_MIN
from ethos.repository.policy.layout.filesystem.core import python_files

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


def ambiguous_module_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find ambiguous module names lacking an exact closed role contract."""
    names = {
        str(name)
        for name in policy.get("ambiguous_module_names", DEFAULT_AMBIGUOUS_MODULE_NAMES)
        if isinstance(name, str) and name
    }
    roles = _ambiguous_module_roles(root, policy)
    findings: list[dict[str, object]] = []
    for path in python_files(root, policy):
        if path.stem not in names:
            continue
        relative = path.relative_to(root).as_posix()
        role = roles.get(relative)
        reasons = _role_reasons(root, path, role)
        if not reasons:
            continue
        findings.append(
            {
                "gap": f"module_layout_ambiguous_module_role:{relative}:{','.join(reasons)}",
                "path": relative,
                "module": path.stem,
                "reasons": reasons,
            }
        )
    return findings


def surface_core_command_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Reject command definitions and declaration targets in CLI ``core.py`` files."""
    declared = _declared_command_modules(root)
    findings: list[dict[str, object]] = []
    for path in python_files(root, policy):
        relative = path.relative_to(root).as_posix()
        if path.name != "core.py" or "/surface/cli/" not in f"/{relative}":
            continue
        module = _module_name(root, path)
        source = path.read_text(encoding="utf-8")
        if module not in declared and ".command(" not in source:
            continue
        findings.append(
            {
                "gap": f"module_layout_surface_core_command:{relative}",
                "path": relative,
            }
        )
    return findings


def multiple_command_owner_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Reject one command module that registers commands on multiple Cyclopts apps."""
    findings: list[dict[str, object]] = []
    for path in python_files(root, policy):
        relative = path.relative_to(root).as_posix()
        if "/surface/cli/" not in f"/{relative}":
            continue
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


def _role_reasons(root: Path, path: Path, role: dict[str, object] | None) -> list[str]:
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
        if public != sorted(str(item) for item in role["public_symbols"]):
            reasons.append("public_drift")
        allowed = tuple(str(item) for item in role["allowed_import_roots"])
        if any(not module.startswith(allowed) for module in _imported_modules(path)):
            reasons.append("import_drift")
    return reasons


def _role_list_reasons(role: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    for field in ("authority_refs", "public_symbols", "allowed_import_roots"):
        value = role.get(field)
        valid = (
            isinstance(value, list) and bool(value) and all(isinstance(item, str) for item in value)
        )
        if not valid:
            reasons.append(f"{field}_invalid")
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


def _declared_command_modules(root: Path) -> set[str]:
    try:
        import tomllib

        payload = tomllib.loads((root / "system/commands.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return set()
    commands = payload.get("commands", [])
    return {
        str(command.get("import_path", "")).partition(":")[0]
        for command in commands
        if isinstance(command, dict) and command.get("import_path")
    }


def _module_name(root: Path, path: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = relative.parts
    return ".".join(parts[1:] if parts and parts[0] == "src" else parts)


def _command_owner(decorator: ast.expr) -> str:
    call = decorator if isinstance(decorator, ast.Call) else None
    target = call.func if call else decorator
    if not isinstance(target, ast.Attribute) or target.attr != "command":
        return ""
    return target.value.id if isinstance(target.value, ast.Name) else ""


def suffix_module_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find suffix-flat module names such as `foo_report.py`."""
    findings: list[dict[str, object]] = []
    for path in python_files(root, policy):
        if path.name == "__init__.py" or path.stem.startswith("_") or "_" not in path.stem:
            continue
        rel = path.relative_to(root).as_posix()
        gap = f"module_layout_suffix_module:{rel}:{path.stem}"
        findings.append({"gap": gap, "path": rel, "module": path.stem})
    return findings


def suffix_group_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find grouped suffix-flat modules sharing one prefix."""
    minimum = int(policy.get("suffix_flat_group_min", DEFAULT_SUFFIX_GROUP_MIN))
    grouped: dict[Path, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for path in python_files(root, policy):
        if path.name == "__init__.py" or path.stem.startswith("_") or "_" not in path.stem:
            continue
        prefix, _suffix = path.stem.split("_", maxsplit=1)
        grouped[path.parent.relative_to(root)][prefix].append(path.name)
    findings: list[dict[str, object]] = []
    for parent, groups in sorted(grouped.items()):
        parent_text = parent.as_posix()
        for prefix, names in sorted(groups.items()):
            if len(names) < minimum:
                continue
            gap = f"module_layout_suffix_flat:{parent_text}:{prefix}:{len(names)}"
            findings.append(
                {"gap": gap, "directory": parent_text, "prefix": prefix, "files": names}
            )
    return findings


def flat_directory_findings(root: Path, policy: dict[str, Any]) -> list[dict[str, object]]:
    """Find directories with too many direct governed Python modules."""
    limit = int(policy.get("flat_directory_limit", DEFAULT_FLAT_DIRECTORY_LIMIT))
    counts: dict[Path, int] = defaultdict(int)
    for path in python_files(root, policy):
        if path.name != "__init__.py":
            counts[path.parent.relative_to(root)] += 1
    findings: list[dict[str, object]] = []
    for directory, count in sorted(counts.items()):
        directory_text = directory.as_posix()
        if count <= limit:
            continue
        gap = f"module_layout_flat_directory:{directory_text}:{count}>{limit}"
        findings.append({"gap": gap, "directory": directory_text, "module_count": count})
    return findings
