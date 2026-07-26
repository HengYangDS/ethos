"""Static alias keys and known execution API catalog entries."""

from __future__ import annotations

import ast

SUBPROCESS_EXECUTION_FUNCTIONS = frozenset(
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
OS_EXECUTABLE_POSITIONS = {
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
OS_EXECUTION_FUNCTIONS = frozenset({"popen", "system"}.union(OS_EXECUTABLE_POSITIONS))
EXECUTION_FUNCTIONS_BY_MODULE = {
    "asyncio": frozenset({"create_subprocess_exec", "create_subprocess_shell"}),
    "os": OS_EXECUTION_FUNCTIONS,
    "subprocess": SUBPROCESS_EXECUTION_FUNCTIONS,
}
ASYNCIO_EXEC_FUNCTION = "asyncio.create_subprocess_exec"
DYNAMIC_EXECUTION_FUNCTION_SUFFIX = ".<dynamic>"
IMPLICIT_SHELL_FUNCTIONS = frozenset(
    {
        "asyncio.create_subprocess_shell",
        "os.popen",
        "os.system",
        "subprocess.getoutput",
        "subprocess.getstatusoutput",
    }
)
POPEN_EXECUTABLE_POSITION = 2
POPEN_SHELL_POSITION = 8


def alias_key(reference: ast.expr) -> str | None:
    """Return a stable key for a statically addressable name, member, or item."""
    if isinstance(reference, ast.Name):
        return reference.id
    if isinstance(reference, ast.Attribute):
        parent = alias_key(reference.value)
        return f"{parent}.{reference.attr}" if parent is not None else None
    if isinstance(reference, ast.Subscript):
        parent = alias_key(reference.value)
        key = literal_subscript_key(reference.slice)
        return f"{parent}[{key}]" if parent is not None and key is not None else None
    return None


def literal_subscript_key(node: ast.expr | None) -> str | None:
    """Return the stable representation of one literal subscript key."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, bytes)):
        return repr(node.value)
    return None


def static_mapping_entries(value: ast.expr) -> tuple[tuple[tuple[str, ...], ast.expr], ...]:
    """Return every statically-addressable leaf of a literal mapping expression."""
    entries: list[tuple[tuple[str, ...], ast.expr]] = []
    for key, item in static_mapping_items(value):
        entries.append(((key,), item))
        for path, nested in static_mapping_entries(item):
            entries.append(((key, *path), nested))
    return tuple(entries)


def static_mapping_items(reference: ast.expr) -> tuple[tuple[str, ast.expr], ...]:
    """Return literal key/value pairs from a dictionary-shaped expression."""
    if isinstance(reference, ast.Dict):
        return tuple(
            (key, value)
            for key_node, value in zip(reference.keys, reference.values, strict=True)
            if value is not None and (key := literal_subscript_key(key_node)) is not None
        )
    if (
        isinstance(reference, ast.Call)
        and isinstance(reference.func, ast.Name)
        and reference.func.id == "dict"
        and not reference.args
        and all(keyword.arg is not None for keyword in reference.keywords)
    ):
        return tuple((repr(keyword.arg), keyword.value) for keyword in reference.keywords)
    return ()
