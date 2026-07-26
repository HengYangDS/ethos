"""Declaration-driven audit of mandatory external executable boundaries."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.repository.policy.coupling.execution.aliases.catalog as catalog
from ethos.repository.policy.coupling.execution.collector import collect_external_execution_calls

if TYPE_CHECKING:
    from ethos_core.contracts.registry.declarations import CouplingBinding
    from ethos_core.contracts.registry.declarations import CouplingDeclaration


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
    gaps.extend(_dynamic_resolution_gaps(tree, relative, binding))
    for node, function in external_execution_calls(tree):
        gaps.extend(_call_gaps(node, function, relative, binding))
    return gaps


def external_execution_calls(tree: ast.AST) -> tuple[tuple[ast.Call, str], ...]:
    """Return external execution calls paired with canonical or fail-closed names."""
    return collect_external_execution_calls(tree)


def _dynamic_resolution_gaps(tree: ast.AST, relative: str, binding: CouplingBinding) -> list[str]:
    """Fail closed on runtime module loading or namespace reflection in mandatory paths."""
    return [
        _node_gap(binding, relative, node, "mandatory_executable_dynamic_resolution")
        for node in ast.walk(tree)
        if _is_dynamic_resolution_node(node)
    ]


def _is_dynamic_resolution_node(node: ast.AST) -> bool:
    """Return whether syntax can resolve an execution module outside lexical analysis."""
    if isinstance(node, ast.ImportFrom):
        return node.module in {"builtins", "importlib"} and any(
            alias.name in {"__import__", "import_module"} for alias in node.names
        )
    if isinstance(node, ast.Name):
        return node.id in {"__import__", "globals", "locals", "vars", "eval", "exec"}
    if isinstance(node, ast.Attribute):
        return node.attr in {"__import__", "import_module", "modules"}
    return isinstance(node, ast.Call) and _is_dynamic_resolution_getattr(node)


def _is_dynamic_resolution_getattr(node: ast.Call) -> bool:
    """Recognize literal reflection of module-loader and module-map attributes."""
    if not isinstance(node.func, ast.Name) or node.func.id != "getattr" or len(node.args) < 2:
        return False
    name = node.args[1]
    return isinstance(name, ast.Constant) and name.value in {
        "__import__",
        "import_module",
        "modules",
    }


def _call_gaps(node: ast.Call, function: str, relative: str, binding: CouplingBinding) -> list[str]:
    if (kind := _immediate_call_gap_kind(node, function)) is not None:
        return [_call_gap(binding, relative, node, kind)]
    if function == catalog.ASYNCIO_EXEC_FUNCTION:
        return _asyncio_exec_gaps(node, relative, binding)
    if (
        function.startswith("os.")
        and function.removeprefix("os.") in catalog.OS_EXECUTABLE_POSITIONS
    ):
        return _os_executable_gaps(node, function, relative, binding)
    gaps: list[str] = []
    if _unsafe_option(
        node,
        "shell",
        position=catalog.POPEN_SHELL_POSITION,
        safe_values={False, None},
    ):
        gaps.append(_call_gap(binding, relative, node, "mandatory_executable_shell_true"))
    if _unsafe_option(
        node,
        "executable",
        position=catalog.POPEN_EXECUTABLE_POSITION,
        safe_values={None},
    ):
        gaps.append(_call_gap(binding, relative, node, "mandatory_executable_override"))
    gaps.extend(_subprocess_argv_gaps(node, relative, binding))
    return gaps


def _immediate_call_gap_kind(node: ast.Call, function: str) -> str | None:
    if function in catalog.IMPLICIT_SHELL_FUNCTIONS:
        return "mandatory_executable_shell_true"
    if any(isinstance(argument, ast.Starred) for argument in node.args):
        return "mandatory_executable_expanded_positionals"
    if any(keyword.arg is None for keyword in node.keywords):
        return "mandatory_executable_expanded_keywords"
    if function.endswith(catalog.DYNAMIC_EXECUTION_FUNCTION_SUFFIX):
        return "mandatory_executable_dynamic_argv0"
    return None


def _os_executable_gaps(
    node: ast.Call,
    function: str,
    relative: str,
    binding: CouplingBinding,
) -> list[str]:
    position = catalog.OS_EXECUTABLE_POSITIONS[function.removeprefix("os.")]
    executable = _argument_at_position_or_keywords(node, position, ("path", "file"))
    return _executable_gaps(executable, node, relative, binding)


def _asyncio_exec_gaps(
    node: ast.Call,
    relative: str,
    binding: CouplingBinding,
) -> list[str]:
    gaps: list[str] = []
    if _unsafe_keyword_option(node, "shell", safe_values={False, None}):
        gaps.append(_call_gap(binding, relative, node, "mandatory_executable_shell_true"))
    if _unsafe_keyword_option(node, "executable", safe_values={None}):
        gaps.append(_call_gap(binding, relative, node, "mandatory_executable_override"))
    executable = node.args[0] if node.args else _keyword_value(node, "program")
    gaps.extend(_executable_gaps(executable, node, relative, binding))
    return gaps


def _subprocess_argv_gaps(
    node: ast.Call,
    relative: str,
    binding: CouplingBinding,
) -> list[str]:
    argv = node.args[0] if node.args else _keyword_value(node, "args")
    if isinstance(argv, ast.Constant) and isinstance(argv.value, str):
        return [_call_gap(binding, relative, node, "mandatory_executable_command_string")]
    if not isinstance(argv, (ast.List, ast.Tuple)) or not argv.elts:
        return [_call_gap(binding, relative, node, "mandatory_executable_dynamic_argv0")]
    return _executable_gaps(argv.elts[0], node, relative, binding)


def _executable_gaps(
    executable: ast.expr | None,
    node: ast.Call,
    relative: str,
    binding: CouplingBinding,
) -> list[str]:
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


def _argument_at_position_or_keywords(
    node: ast.Call,
    position: int,
    names: tuple[str, ...],
) -> ast.expr | None:
    if len(node.args) > position:
        return node.args[position]
    for name in names:
        value = _keyword_value(node, name)
        if value is not None:
            return value
    return None


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


def _unsafe_keyword_option(node: ast.Call, name: str, *, safe_values: set[object]) -> bool:
    value = _keyword_value(node, name)
    return value is not None and not (
        isinstance(value, ast.Constant) and value.value in safe_values
    )


def _path_gap(binding: CouplingBinding, relative: str, kind: str) -> str:
    return f"{kind}:{binding.id}:{relative}"


def _node_gap(binding: CouplingBinding, relative: str, node: ast.AST, kind: str) -> str:
    """Return one source-location-bound gap for an audited syntax node."""
    return f"{_path_gap(binding, relative, kind)}:{node.lineno}"


def _call_gap(binding: CouplingBinding, relative: str, node: ast.Call, kind: str) -> str:
    return _node_gap(binding, relative, node, kind)
