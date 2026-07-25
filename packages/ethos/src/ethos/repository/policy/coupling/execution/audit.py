"""Declaration-driven audit of mandatory external executable boundaries."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ethos_core.contracts.registry.declarations import CouplingBinding
    from ethos_core.contracts.registry.declarations import CouplingDeclaration

_EXECUTION_FUNCTIONS = frozenset(
    {
        "Popen",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
        "run",
    }
)
_IMPLICIT_SHELL_FUNCTIONS = frozenset({"getoutput", "getstatusoutput"})
_POPEN_EXECUTABLE_POSITION = 2
_POPEN_SHELL_POSITION = 8


def mandatory_executable_gaps(root: Path, declaration: CouplingDeclaration) -> list[str]:
    """Return gaps for declared mandatory paths that cross unsafe process boundaries."""
    audit_root = root.resolve()
    gaps: list[str] = []
    for binding in declaration.bindings:
        if not binding.audit_root_bound:
            continue
        for relative in binding.mandatory_paths:
            path = _audit_path(audit_root, relative)
            if path is None:
                gaps.append(_path_gap(binding, relative, "mandatory_executable_path_escape"))
                continue
            if not path.is_file():
                gaps.append(_path_gap(binding, relative, "mandatory_executable_path_missing"))
                continue
            gaps.extend(_source_gaps(path, relative, binding))
    return sorted(gaps)


def _audit_path(root: Path, relative: str) -> Path | None:
    declared = Path(relative)
    if declared.is_absolute() or ".." in declared.parts:
        return None
    candidate = root / declared
    resolved = candidate.resolve(strict=False)
    return resolved if resolved.is_relative_to(root) else None


def _source_gaps(path: Path, relative: str, binding: CouplingBinding) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError):
        return [_path_gap(binding, relative, "mandatory_executable_source_unavailable")]
    gaps: list[str] = []
    for node, function in subprocess_execution_calls(tree):
        gaps.extend(_call_gaps(node, function, relative, binding))
    return gaps


def subprocess_execution_calls(tree: ast.AST) -> tuple[tuple[ast.Call, str], ...]:
    """Return subprocess execution calls paired with their canonical function names."""
    module_aliases, function_aliases = _subprocess_aliases(tree)
    calls: list[tuple[ast.Call, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = _execution_function(node, module_aliases, function_aliases)
        if function is not None:
            calls.append((node, function))
    return tuple(calls)


def _subprocess_aliases(tree: ast.AST) -> tuple[set[str], dict[str, str]]:
    module_aliases: set[str] = set()
    function_aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            module_aliases.update(
                alias.asname or alias.name for alias in node.names if alias.name == "subprocess"
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            function_aliases.update(
                {
                    alias.asname or alias.name: alias.name
                    for alias in node.names
                    if alias.name in _EXECUTION_FUNCTIONS
                }
            )
    return module_aliases, function_aliases


def _execution_function(
    node: ast.Call, module_aliases: set[str], function_aliases: dict[str, str]
) -> str | None:
    function = node.func
    if isinstance(function, ast.Name):
        return function_aliases.get(function.id)
    if (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id in module_aliases
        and function.attr in _EXECUTION_FUNCTIONS
    ):
        return function.attr
    return None


def _call_gaps(node: ast.Call, function: str, relative: str, binding: CouplingBinding) -> list[str]:
    if function in _IMPLICIT_SHELL_FUNCTIONS:
        return [_call_gap(binding, relative, node, "mandatory_executable_shell_true")]
    if any(isinstance(argument, ast.Starred) for argument in node.args):
        return [
            _call_gap(
                binding,
                relative,
                node,
                "mandatory_executable_expanded_positionals",
            )
        ]
    if any(keyword.arg is None for keyword in node.keywords):
        return [_call_gap(binding, relative, node, "mandatory_executable_expanded_keywords")]
    gaps: list[str] = []
    if _unsafe_option(
        node,
        "shell",
        position=_POPEN_SHELL_POSITION,
        safe_values={False, None},
    ):
        gaps.append(_call_gap(binding, relative, node, "mandatory_executable_shell_true"))
    if _unsafe_option(
        node,
        "executable",
        position=_POPEN_EXECUTABLE_POSITION,
        safe_values={None},
    ):
        gaps.append(_call_gap(binding, relative, node, "mandatory_executable_override"))
    gaps.extend(_argv_gaps(node, relative, binding))
    return gaps


def _argv_gaps(node: ast.Call, relative: str, binding: CouplingBinding) -> list[str]:
    argv = node.args[0] if node.args else _keyword_value(node, "args")
    if isinstance(argv, ast.Constant) and isinstance(argv.value, str):
        return [_call_gap(binding, relative, node, "mandatory_executable_command_string")]
    if not isinstance(argv, (ast.List, ast.Tuple)) or not argv.elts:
        return [_call_gap(binding, relative, node, "mandatory_executable_dynamic_argv0")]
    executable = argv.elts[0]
    if not isinstance(executable, ast.Constant) or not isinstance(executable.value, str):
        return [_call_gap(binding, relative, node, "mandatory_executable_dynamic_argv0")]
    if executable.value not in binding.declared_executables:
        return [
            f"{_call_gap(binding, relative, node, 'mandatory_executable_undeclared')}"
            f":{executable.value}"
        ]
    return []


def _keyword_value(node: ast.Call, name: str) -> ast.expr | None:
    return next((keyword.value for keyword in node.keywords if keyword.arg == name), None)


def _unsafe_option(
    node: ast.Call,
    name: str,
    *,
    position: int,
    safe_values: set[object],
) -> bool:
    values = list(node.args[position : position + 1])
    keyword = _keyword_value(node, name)
    if keyword is not None:
        values.append(keyword)
    return any(
        not (isinstance(value, ast.Constant) and value.value in safe_values) for value in values
    )


def _path_gap(binding: CouplingBinding, relative: str, kind: str) -> str:
    return f"{kind}:{binding.id}:{relative}"


def _call_gap(binding: CouplingBinding, relative: str, node: ast.Call, kind: str) -> str:
    return f"{_path_gap(binding, relative, kind)}:{node.lineno}"
