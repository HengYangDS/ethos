"""Imports, executables, commands, and runtime inputs from Python syntax."""

from __future__ import annotations

import ast
import re
import shlex
import warnings
from typing import TYPE_CHECKING

from ethos.repository.policy.references.commands import command_executables
from ethos.repository.policy.references.commands import normalize_command

if TYPE_CHECKING:
    from collections.abc import Mapping

_SUBPROCESS_CALLS = {"run", "Popen", "check_call", "check_output"}


def python_trees(text: str) -> tuple[ast.AST, ...]:
    """Parse complete Python or independent added lines with valid Python syntax."""
    try:
        return (_parse_without_syntax_warnings(text),)
    except SyntaxError:
        trees = []
        for line in text.splitlines():
            candidate = line
            if line.lstrip().startswith("@"):
                candidate += "\ndef _binding_probe() -> None:\n    pass"
            try:
                trees.append(_parse_without_syntax_warnings(candidate))
            except SyntaxError:
                continue
        return tuple(trees)


def complete_python_tree(text: str) -> ast.AST | None:
    """Parse one complete Python carrier without fragment fallback."""
    try:
        return _parse_without_syntax_warnings(text)
    except SyntaxError:
        return None


def _parse_without_syntax_warnings(text: str) -> ast.AST:
    """Treat warning-producing snippets as invalid partial Python syntax."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", SyntaxWarning)
        return ast.parse(text)


def python_references(
    tree: ast.AST,
    npm_scripts: dict[str, set[str]],
) -> tuple[set[str], set[str], set[str]]:
    """Extract imports, executables, and runtime inputs in one AST traversal."""
    imports: set[str] = set()
    executables: set[str] = set()
    inputs: set[str] = set()
    constants = {
        target.id: value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance((target := node.targets[0]), ast.Name)
        and (value := _string(node.value))
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            executables.update(_call_executables(node, npm_scripts))
            owner = node.func.value if isinstance(node.func, ast.Attribute) else None
            name = node.func.attr if isinstance(node.func, ast.Attribute) else ""
            value = _string(node.args[0]) if node.args else ""
            if not value and node.args and isinstance(node.args[0], ast.Name):
                value = constants.get(node.args[0].id, "")
            if value and _is_environment_read(owner, name):
                inputs.add(value)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if (
                isinstance(target, ast.Name)
                and re.search(r"(?:COMMAND|CMD|EXECUTABLE|BINARY|CLI|TOOL)$", target.id)
                and isinstance(node.value, ast.List | ast.Tuple)
            ):
                executables.update(
                    command_executables(_literal_command_tokens(node.value), npm_scripts)
                )
    return imports, executables, inputs


def _is_environment_read(owner: ast.AST | None, name: str) -> bool:
    return (isinstance(owner, ast.Name) and owner.id == "os" and name == "getenv") or (
        isinstance(owner, ast.Attribute)
        and isinstance(owner.value, ast.Name)
        and owner.value.id == "os"
        and owner.attr == "environ"
        and name == "get"
    )


def _call_executables(node: ast.Call, npm_scripts: dict[str, set[str]]) -> set[str]:
    name = node.func.id if isinstance(node.func, ast.Name) else ""
    attribute = node.func.attr if isinstance(node.func, ast.Attribute) else ""
    owner = (
        node.func.value.id
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
        else ""
    )
    if node.args and (owner == "subprocess" and attribute in _SUBPROCESS_CALLS):
        return command_executables(_literal_command_tokens(node.args[0]), npm_scripts)
    if node.args and owner == "shutil" and attribute == "which":
        return {_string(node.args[0])} - {""}
    if (
        name == "Path"
        and node.args
        and (value := _string(node.args[0]))
        and value.startswith(("/bin/", "/usr/bin/", "/usr/local/bin/"))
    ):
        return {value.rsplit("/", maxsplit=1)[-1]}
    return set()


def _literal_command_tokens(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            return tuple(shlex.split(node.value))
        except ValueError:
            return ()
    if isinstance(node, ast.List | ast.Tuple):
        values = []
        for item in node.elts:
            if not (value := _string(item)):
                break
            values.append(value)
        return tuple(values)
    return ()


def _string(node: ast.AST) -> str:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ""


def cyclopts_prefixes(
    files: dict[str, str],
    *,
    parsed_files: Mapping[str, ast.AST | None] | None = None,
) -> dict[tuple[str, str], str]:
    """Discover command prefixes declared by Cyclopts application trees."""
    applications: dict[tuple[str, str], str] = {}
    modules: dict[str, tuple[ast.AST, dict[str, tuple[str, str]]]] = {}
    for path, text in files.items():
        if "App(" not in text:
            continue
        tree = parsed_files.get(path) if parsed_files is not None else None
        trees = (
            (tree,)
            if tree is not None
            else (() if parsed_files is not None else python_trees(text))
        )
        if not trees:
            continue
        tree = trees[0]
        module = module_name(path)
        imported = {
            alias.asname or alias.name: (import_module(path, node), alias.name)
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        applications.update(
            {
                (module, target.id): _app_name(node.value, target.id)
                for node in ast.walk(tree)
                if isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance((target := node.targets[0]), ast.Name)
                and _is_app(node.value)
            }
        )
        modules[module] = tree, imported
    parents: dict[tuple[str, str], tuple[str, str]] = {}
    for module, (tree, imported) in modules.items():
        parents.update(
            {
                _app_key(module, imported, node.args[0].id): _app_key(
                    module, imported, node.func.value.id
                )
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "command"
                and isinstance(node.func.value, ast.Name)
                and node.args
                and isinstance(node.args[0], ast.Name)
                and _app_key(module, imported, node.args[0].id) in applications
            }
        )
        for node in ast.walk(tree):
            if not isinstance(node, ast.For) or not isinstance(node.iter, ast.Tuple | ast.List):
                continue
            parent = next(
                (
                    _app_key(module, imported, call.func.value.id)
                    for call in ast.walk(node)
                    if isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "command"
                    and isinstance(call.func.value, ast.Name)
                ),
                None,
            )
            if parent is not None:
                parents.update(
                    {
                        _app_key(module, imported, item.id): parent
                        for item in node.iter.elts
                        if isinstance(item, ast.Name)
                        and _app_key(module, imported, item.id) in applications
                    }
                )
    return {
        key: _resolve_app_prefix(key, applications=applications, parents=parents)
        for key in applications
    }


def _app_key(
    module: str,
    imported: dict[str, tuple[str, str]],
    name: str,
) -> tuple[str, str]:
    return imported.get(name, (module, name))


def _resolve_app_prefix(
    key: tuple[str, str],
    *,
    applications: dict[tuple[str, str], str],
    parents: dict[tuple[str, str], tuple[str, str]],
    trail: frozenset[tuple[str, str]] = frozenset(),
) -> str:
    if key in trail or key not in applications:
        return ""
    parent = (
        _resolve_app_prefix(
            parents[key],
            applications=applications,
            parents=parents,
            trail=trail | {key},
        )
        if key in parents
        else ""
    )
    return " ".join(part for part in (parent, applications[key]) if part)


def _is_app(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and (
        (isinstance(node.func, ast.Name) and node.func.id == "App")
        or (isinstance(node.func, ast.Attribute) and node.func.attr == "App")
    )


def _app_name(node: ast.AST, variable: str) -> str:
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == "name" and (name := _string(keyword.value)):
                return name
    return variable.removesuffix("_app").replace("_", "-")


def module_name(path: str) -> str:
    parts = path.removeprefix("src/").removesuffix(".py").split("/")
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def import_module(path: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    package = module_name(path).split(".")[: -node.level]
    return ".".join((*package, *((node.module or "").split("."))))


def cyclopts_command_owners(
    path: str,
    tree: ast.AST,
    prefixes: dict[tuple[str, str], str],
) -> dict[str, set[str]]:
    """Return command identities with their exact defining symbols."""
    imported = {
        alias.asname or alias.name: (import_module(path, node), alias.name)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    owners: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            owner, names = _command_names(decorator, node.name)
            key = imported.get(owner, (module_name(path), owner))
            prefix = prefixes.get(key, "")
            if not prefix:
                candidates = {value for (_, name), value in prefixes.items() if name == owner}
                prefix = candidates.pop() if len(candidates) == 1 else ""
            for name in names:
                command = normalize_command(" ".join(part for part in (prefix, name) if part))
                owners.setdefault(command, set()).add(f"{path}:{node.name}")
    return owners


def _command_names(decorator: ast.AST, function_name: str) -> tuple[str, tuple[str, ...]]:
    call = decorator if isinstance(decorator, ast.Call) else None
    reference = call.func if call is not None else decorator
    if not (
        isinstance(reference, ast.Attribute)
        and reference.attr == "command"
        and isinstance(reference.value, ast.Name)
    ):
        return "", ()
    names = ()
    for keyword in call.keywords if call is not None else ():
        if keyword.arg == "name" and (name := _string(keyword.value)):
            names = (name,)
    return reference.value.id, names or (function_name.replace("_", "-"),)
