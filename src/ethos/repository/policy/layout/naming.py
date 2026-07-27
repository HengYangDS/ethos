from __future__ import annotations

import ast
from typing import TYPE_CHECKING
from typing import Any

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


def ambiguous_module_findings(
    root: Path,
    policy: dict[str, Any],
    files: tuple[Path, ...] | None = None,
) -> list[dict[str, object]]:
    """Find repository-owned modules whose names do not state a narrow concept."""
    names = {
        str(name)
        for name in policy.get("ambiguous_module_names", DEFAULT_AMBIGUOUS_MODULE_NAMES)
        if isinstance(name, str) and name
    }
    findings: list[dict[str, object]] = []
    for path in semantic_python_files(root, policy, files=files):
        module = path.stem.lstrip("_")
        if module not in names:
            continue
        relative = path.relative_to(root).as_posix()
        findings.append(
            {
                "gap": f"module_layout_ambiguous_module:{relative}",
                "path": relative,
                "module": module,
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


def _command_owner(decorator: ast.expr) -> str:
    call = decorator if isinstance(decorator, ast.Call) else None
    target = call.func if call else decorator
    if not isinstance(target, ast.Attribute) or target.attr != "command":
        return ""
    return target.value.id if isinstance(target.value, ast.Name) else ""
