"""Detect ambiguous module names and competing command owners."""

from __future__ import annotations

import ast
import re
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


def identifier_naming_findings(source: str, *, path: str) -> tuple[dict[str, object], ...]:
    """Require semantic code identities; protocol-version values are not bindings."""
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        line = error.lineno or 0
        return ({"gap": f"code_identifier_syntax:{path}:{line}", "path": path, "line": line},)
    bindings = set()
    for node in ast.walk(tree):
        match node:
            case (
                ast.FunctionDef(name=name)
                | ast.AsyncFunctionDef(name=name)
                | ast.ClassDef(name=name)
                | ast.arg(arg=name)
                | ast.Name(id=name, ctx=ast.Store())
                | ast.Attribute(attr=name, ctx=ast.Store())
            ):
                bindings.add((node.lineno, name))
            case ast.alias(name=imported, asname=alias):
                bindings.add((node.lineno, alias or imported.split(".")[0]))
            case (
                ast.ExceptHandler(name=str() as name)
                | ast.MatchAs(name=str() as name)
                | ast.MatchStar(name=str() as name)
                | ast.MatchMapping(rest=str() as name)
            ):
                bindings.add((node.lineno, name))
    return tuple(
        {
            "gap": f"code_identifier_semantics:{path}:{line}:{name}",
            "path": path,
            "line": line,
            "identifier": name,
        }
        for line, name in sorted(bindings)
        if any(
            re.fullmatch(r"[vV][0-9]+", token)
            for token in re.split(r"_+|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z0-9])", name)
        )
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
        ambiguous = sorted(_name_tokens(module).intersection(names))
        if not ambiguous:
            continue
        relative = path.relative_to(root).as_posix()
        findings.append(
            {
                "gap": f"module_layout_ambiguous_module:{relative}",
                "path": relative,
                "module": module,
                "ambiguous_tokens": ambiguous,
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
        if _name_tokens(directory.name.lstrip("_")).intersection(names)
    ]


def _name_tokens(name: str) -> set[str]:
    """Return semantic words from snake-case repository-owned Python names."""
    return {token for token in name.split("_") if token}


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
