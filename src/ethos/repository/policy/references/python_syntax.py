"""Imports, executables, commands, and runtime inputs from Python syntax."""

from __future__ import annotations

import ast
import warnings
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ethos.repository.policy.references.commands import command_executables
from ethos.repository.policy.references.commands import normalize_command
from ethos.repository.policy.references.commands import split_command

if TYPE_CHECKING:
    from collections.abc import Mapping

_SINKS = {
    "subprocess.run": "command",
    "subprocess.Popen": "command",
    "subprocess.check_call": "command",
    "subprocess.check_output": "command",
    "shutil.which": "executable",
    "pathlib.Path": "path",
    "os.getenv": "value",
    "os.environ.get": "value",
}
_MODULES = frozenset({"os", "shutil", "subprocess"})
_BINARIES = ("/bin/", "/usr/bin/", "/usr/local/bin/")
_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
_BINDERS = (ast.Name, ast.Import, ast.ImportFrom, ast.arg, *_SCOPES)
# A name bound only through names this deep is not followed further.
_DEPTH = 8


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
    tree: ast.AST, npm_scripts: dict[str, set[str]]
) -> tuple[set[str], set[str], set[str], bool]:
    """Extract imports, executables, runtime inputs and dynamic sink lookup through bindings."""
    bindings = _Bindings(tree)
    executables: set[str] = set()
    inputs: set[str] = set()
    dynamic = False
    for node in bindings.sites:
        if isinstance(node, ast.Subscript) and "os.environ" in bindings.values(node.value):
            inputs.update(bindings.strings(node.slice))
        elif isinstance(node, ast.Call):
            for callee in bindings.values(node.func):
                kind = _SINKS.get(callee, "") if isinstance(callee, str) else ""
                found = _sink_references(kind, node.args[0], bindings, npm_scripts)
                (inputs if kind == "value" else executables).update(found)
                # A sink chosen at run time cannot be observed, so its file is unknown.
                dynamic |= isinstance(callee, _Name) and callee == _DYNAMIC
    return bindings.imports, executables, inputs, dynamic


def _sink_references(
    kind: str, operand: ast.expr, bindings: _Bindings, npm_scripts: dict[str, set[str]]
) -> set[str]:
    """The executables or inputs one sink call references through its first argument."""
    if kind == "command":
        return {
            executable
            for tokens in bindings.commands(operand)
            for executable in command_executables(
                tokens, npm_scripts, module_imports=bindings.imports
            )
        }
    strings = bindings.strings(operand) if kind else set()
    if kind == "path":
        return {text.rsplit("/", 1)[-1] for text in strings if text.startswith(_BINARIES)}
    return strings


class _Name(str):
    """A qualified name an import, attribute or builtin binds, as opposed to a string value."""

    __slots__ = ()


# An attribute of a sink module that getattr selects by a computed name.
_DYNAMIC = _Name("*")


_Binding = ast.expr | _Name | None
_Value = str | tuple[str, ...]


class _Bindings:
    """Each scope's name bindings and the program position after which each holds."""

    def __init__(self, tree: ast.AST) -> None:
        self.module = tree
        self.parent: dict[ast.AST, ast.AST] = {}
        self.imports: set[str] = set()
        self.sites: list[ast.AST] = []
        raw: list[tuple[ast.AST, str, tuple[int, int], _Binding]] = []
        declared: dict[tuple[ast.AST, str], ast.AST] = {}
        stack = [tree]
        while stack:
            node = stack.pop()
            children = tuple(ast.iter_child_nodes(node))
            self.parent.update(dict.fromkeys(children, node))
            stack.extend(children)
            if (isinstance(node, ast.Call) and node.args) or (
                isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load)
            ):
                self.sites.append(node)
            elif isinstance(node, ast.Global | ast.Nonlocal):
                scope = self.scope(node)
                owner = self.module if isinstance(node, ast.Global) else self.enclosing(scope)
                declared.update(dict.fromkeys(((scope, name) for name in node.names), owner))
            elif isinstance(node, _BINDERS) and (bound := self.bound(node)):
                scope = self.scope(node)
                position = (0, 0) if isinstance(node, ast.arg) else self.effect(node)
                raw.extend((scope, name, position, value) for name, value in bound.items())
        self.names: dict[ast.AST, dict[str, list[tuple[tuple[int, int], _Binding]]]] = {}
        for scope, name, position, value in raw:
            owner = declared.get((scope, name), scope)
            self.names.setdefault(owner, {}).setdefault(name, []).append((position, value))

    def bound(self, node: ast.AST) -> dict[str, _Binding]:
        """The names one node binds, each with its assigned expression, import or nothing known."""
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            owner = self.parent[node]
            simple = isinstance(owner, ast.AnnAssign | ast.NamedExpr) or (
                isinstance(owner, ast.Assign) and node in owner.targets
            )
            return {node.id: getattr(owner, "value", None) if simple else None}
        if isinstance(node, ast.Import | ast.ImportFrom):
            modules = (
                [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
            )
            self.imports.update(module.split(".")[0] for module in modules if module)
            return {
                alias.asname or alias.name.split(".")[0]: _Name(
                    f"{node.module}.{alias.name}"
                    if isinstance(node, ast.ImportFrom)
                    else alias.name
                    if alias.asname
                    else alias.name.split(".")[0]
                )
                for alias in node.names
            }
        if isinstance(node, ast.arg | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            return {node.arg if isinstance(node, ast.arg) else node.name: None}
        return {}

    def scope(self, node: ast.AST) -> ast.AST:
        """The innermost function, lambda, class or module a node binds or reads in."""
        current = self.parent.get(node)
        while current is not None and not isinstance(current, _SCOPES):
            current = self.parent.get(current)
        return current or self.module

    def enclosing(self, scope: ast.AST) -> ast.AST:
        """The scope whose names a nested scope reads; a class body is never one."""
        scope = self.scope(scope)
        while isinstance(scope, ast.ClassDef):
            scope = self.scope(scope)
        return scope

    def effect(self, node: ast.AST) -> tuple[int, int]:
        """A binding holds once the statement that makes it completes."""
        while not isinstance(node, ast.stmt):
            node = self.parent[node]
        return (node.end_lineno or 0, node.end_col_offset or 0)

    def reaching(self, name: str, site: ast.expr) -> list[_Binding] | None:
        """The bindings that can hold at a site, or None when only a builtin can."""
        reader = scope = self.scope(site)
        while (entries := self.names.get(scope, {}).get(name)) is None and scope is not self.module:
            scope = self.enclosing(scope)
        if entries is None:
            return None
        current, looped = self.parent.get(site), False
        while current is not None and current is not scope:
            looped |= isinstance(current, ast.For | ast.AsyncFor | ast.While)
            current = self.parent.get(current)
        if scope is reader and not looped:
            entries = [entry for entry in entries if entry[0] <= (site.lineno, site.col_offset)]
        return [value for _, value in entries]

    def values(self, node: ast.AST | None, depth: int = 0) -> set[_Value]:
        """The strings, literal argv prefixes and qualified names an expression can hold."""
        if text := _string(node) if node is not None else "":
            return {text}
        if isinstance(node, ast.Name) and depth < _DEPTH:
            found = self.reaching(node.id, node)
            # An unbound name is a builtin, or a module a fragment uses without importing it.
            builtin = [_Name("pathlib.Path" if node.id == "Path" else node.id)]
            return {
                value
                for binding in (builtin if found is None else found)
                for value in (
                    {binding} if isinstance(binding, _Name) else self.values(binding, depth + 1)
                )
            }
        if isinstance(node, ast.Attribute | ast.Call):
            return self.attributes(node, depth)
        if isinstance(node, ast.List | ast.Tuple):
            tokens: list[str] = []
            for element in node.elts:
                if len(found := self.strings(element)) != 1:
                    break
                tokens.append(found.pop())
            return {tuple(tokens)}
        return set()

    def attributes(self, node: ast.Attribute | ast.Call, depth: int) -> set[_Value]:
        """The qualified names an attribute, or a getattr call, selects from its owners."""
        if isinstance(node, ast.Attribute):
            owner, attribute = node.value, node.attr
        elif len(node.args) == 2 and "getattr" in self.values(node.func, depth):
            owner, attribute = node.args[0], _string(node.args[1])
        else:
            return set()
        owners = {name for name in self.values(owner, depth) if isinstance(name, _Name)}
        if attribute:
            return {_Name(f"{name}.{attribute}") for name in owners}
        return {_DYNAMIC} if any(name.split(".")[0] in _MODULES for name in owners) else set()

    def strings(self, node: ast.AST) -> set[str]:
        """The plain string values an expression can hold."""
        return {value for value in self.values(node) if type(value) is str}

    def commands(self, node: ast.AST) -> list[tuple[str, ...]]:
        """The literal argv prefixes an expression can hold, splitting command strings."""
        commands = []
        for value in self.values(node):
            if isinstance(value, tuple):
                commands.append(value)
            elif type(value) is str and (tokens := split_command(value)):
                commands.append(tokens)
        return commands


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
        imported = _from_imports(path, tree)
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


def module_source_paths(module: str, paths: tuple[str, ...]) -> tuple[str, ...]:
    """Bind observed module entry candidates and importing packages without executing them."""
    stem = module.replace(".", "/")
    candidates = {
        f"{prefix}{stem}{ending}" for prefix in ("", "src/") for ending in (".py", "/__main__.py")
    }
    entries = tuple(path for path in paths if path in candidates)
    packages = tuple(
        parent.as_posix() + "/__init__.py"
        for entry in entries
        for parent in PurePosixPath(entry).parents
        if parent != PurePosixPath() and parent.as_posix() + "/__init__.py" in paths
    )
    return tuple(dict.fromkeys((*entries, *packages))) if entries else (stem + ".py",)


def _from_imports(path: str, tree: ast.AST) -> dict[str, tuple[str, str]]:
    """Map each name a from-import binds to its resolved module and imported attribute."""
    return {
        alias.asname or alias.name: (import_module(path, node), alias.name)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }


def import_module(path: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    package = module_name(path).split(".")
    if not path.endswith("/__init__.py"):
        package.pop()
    package = package[: max(0, len(package) - node.level + 1)]
    return ".".join((*package, *(node.module.split(".") if node.module else ())))


def cyclopts_command_owners(
    path: str,
    tree: ast.AST,
    prefixes: dict[tuple[str, str], str],
) -> dict[str, set[str]]:
    """Return command identities with their exact defining symbols."""
    imported = _from_imports(path, tree)
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


def deleted_python_input_gaps(
    files: Mapping[str, str], deleted: frozenset[str]
) -> tuple[list[str], list[str]]:
    """Join native import relations to deleted modules without guessing dynamic imports."""
    current = {module_name(path) for path in files if path.endswith(".py")}
    retired = {
        module_name(path): path
        for path in deleted
        if path.endswith(".py") and module_name(path) not in current
    }
    gaps, unknown = [], []
    if not retired:
        return gaps, unknown
    for path, text in files.items():
        if not path.endswith(".py"):
            continue
        tree = complete_python_tree(text)
        if tree is None:
            unknown.append(f"deleted_input_observation_unknown:{path}:import")
            continue
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                parent = import_module(path, node)
                imported.add(parent)
                imported.update(f"{parent}.{alias.name}" for alias in node.names)
        gaps.extend(
            f"deleted_input:{retired[module]}:{path}:import"
            for module in sorted(imported & retired.keys())
        )
    return gaps, unknown
