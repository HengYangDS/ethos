"""Declaration-driven audit of mandatory external executable boundaries."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ethos_core.contracts.registry.declarations import CouplingBinding
    from ethos_core.contracts.registry.declarations import CouplingDeclaration

_SUBPROCESS_EXECUTION_FUNCTIONS = frozenset(
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
_OS_EXECUTABLE_POSITIONS = {
    "execl": 0,
    "execle": 0,
    "execlp": 0,
    "execlpe": 0,
    "execv": 0,
    "execve": 0,
    "execvp": 0,
    "execvpe": 0,
    "posix_spawn": 0,
    "posix_spawnp": 0,
    "spawnl": 1,
    "spawnle": 1,
    "spawnlp": 1,
    "spawnlpe": 1,
    "spawnv": 1,
    "spawnve": 1,
    "spawnvp": 1,
    "spawnvpe": 1,
}
_OS_EXECUTION_FUNCTIONS = frozenset({"popen", "system"}.union(_OS_EXECUTABLE_POSITIONS))
_EXECUTION_FUNCTIONS_BY_MODULE = {
    "asyncio": frozenset({"create_subprocess_exec", "create_subprocess_shell"}),
    "os": _OS_EXECUTION_FUNCTIONS,
    "subprocess": _SUBPROCESS_EXECUTION_FUNCTIONS,
}
_ASYNCIO_EXEC_FUNCTION = "asyncio.create_subprocess_exec"
_DYNAMIC_EXECUTION_FUNCTION_SUFFIX = ".<dynamic>"
_IMPLICIT_SHELL_FUNCTIONS = frozenset(
    {
        "asyncio.create_subprocess_shell",
        "os.popen",
        "os.system",
        "subprocess.getoutput",
        "subprocess.getstatusoutput",
    }
)
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
    for node, function in external_execution_calls(tree):
        gaps.extend(_call_gaps(node, function, relative, binding))
    return gaps


def external_execution_calls(tree: ast.AST) -> tuple[tuple[ast.Call, str], ...]:
    """Return external execution calls paired with canonical or fail-closed names."""
    module_aliases, function_aliases = _execution_aliases(tree)
    calls: list[tuple[ast.Call, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = _execution_function(node, module_aliases, function_aliases)
        if function is not None:
            calls.append((node, function))
    return tuple(calls)


def _execution_aliases(tree: ast.AST) -> tuple[dict[str, str], dict[str, str]]:
    module_aliases: dict[str, str] = {}
    function_aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _EXECUTION_FUNCTIONS_BY_MODULE:
                    module_aliases[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                function = _canonical_execution_function(node.module, alias.name)
                if function is not None:
                    function_aliases[alias.asname or alias.name] = function
    _assigned_execution_aliases(tree, module_aliases, function_aliases)
    return module_aliases, function_aliases


def _assigned_execution_aliases(
    tree: ast.AST,
    module_aliases: dict[str, str],
    function_aliases: dict[str, str],
) -> None:
    assignments = tuple(
        node for node in ast.walk(tree) if isinstance(node, (ast.Assign, ast.AnnAssign))
    )
    changed = True
    while changed:
        changed = False
        for assignment in assignments:
            value = assignment.value
            if value is None:
                continue
            module = _module_reference(value, module_aliases)
            function = _execution_reference(
                value,
                module_aliases,
                function_aliases,
            )
            for target in _assignment_targets(assignment):
                if not isinstance(target, ast.Name):
                    continue
                if module is not None and target.id not in module_aliases:
                    module_aliases[target.id] = module
                    changed = True
                if function is not None and target.id not in function_aliases:
                    function_aliases[target.id] = function
                    changed = True


def _assignment_targets(assignment: ast.Assign | ast.AnnAssign) -> tuple[ast.expr, ...]:
    if isinstance(assignment, ast.Assign):
        return tuple(assignment.targets)
    return (assignment.target,)


def _execution_function(
    node: ast.Call,
    module_aliases: dict[str, str],
    function_aliases: dict[str, str],
) -> str | None:
    return _execution_reference(node.func, module_aliases, function_aliases)


def _execution_reference(
    function: ast.expr,
    module_aliases: dict[str, str],
    function_aliases: dict[str, str],
) -> str | None:
    if isinstance(function, ast.Name):
        return function_aliases.get(function.id)
    if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
        module = module_aliases.get(function.value.id)
        if module is not None:
            return _canonical_execution_function(module, function.attr)
    if isinstance(function, ast.Call):
        return _getattr_execution_reference(function, module_aliases)
    return None


def _module_reference(reference: ast.expr, module_aliases: dict[str, str]) -> str | None:
    if isinstance(reference, ast.Name):
        return module_aliases.get(reference.id)
    return None


def _getattr_execution_reference(
    reference: ast.Call,
    module_aliases: dict[str, str],
) -> str | None:
    if not isinstance(reference.func, ast.Name) or reference.func.id != "getattr":
        return None
    if not reference.args:
        return None
    module = _module_reference(reference.args[0], module_aliases)
    if module is None:
        return None
    if len(reference.args) < 2:
        return _dynamic_execution_function(module)
    attribute = reference.args[1]
    if isinstance(attribute, ast.Constant) and isinstance(attribute.value, str):
        return _canonical_execution_function(module, attribute.value)
    return _dynamic_execution_function(module)


def _dynamic_execution_function(module: str) -> str:
    return f"{module}{_DYNAMIC_EXECUTION_FUNCTION_SUFFIX}"


def _canonical_execution_function(module: str, function: str) -> str | None:
    declared = _EXECUTION_FUNCTIONS_BY_MODULE.get(module)
    return f"{module}.{function}" if declared is not None and function in declared else None


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
    if function.endswith(_DYNAMIC_EXECUTION_FUNCTION_SUFFIX):
        return [_call_gap(binding, relative, node, "mandatory_executable_dynamic_argv0")]
    if function == _ASYNCIO_EXEC_FUNCTION:
        return _asyncio_exec_gaps(node, relative, binding)
    if function.startswith("os.") and function.removeprefix("os.") in _OS_EXECUTABLE_POSITIONS:
        return _os_executable_gaps(node, function, relative, binding)
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
    gaps.extend(_subprocess_argv_gaps(node, relative, binding))
    return gaps


def _os_executable_gaps(
    node: ast.Call,
    function: str,
    relative: str,
    binding: CouplingBinding,
) -> list[str]:
    position = _OS_EXECUTABLE_POSITIONS[function.removeprefix("os.")]
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


def _call_gap(binding: CouplingBinding, relative: str, node: ast.Call, kind: str) -> str:
    return f"{_path_gap(binding, relative, kind)}:{node.lineno}"
