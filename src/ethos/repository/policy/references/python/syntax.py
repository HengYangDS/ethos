"""Imports, executables, commands, and runtime inputs from Python syntax."""

from __future__ import annotations

import ast
import symtable
import warnings
from dataclasses import dataclass
from dataclasses import field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ethos.repository.policy.references.commands.vocabulary import normalize_command

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class LexicalBindings:
    """Compiler-owned classification, independent of statement-order value facts."""

    locals: frozenset[str]
    globals: frozenset[str]
    nonlocals: frozenset[str]
    outer_writes: frozenset[str]
    free: frozenset[str]

    @classmethod
    def from_table(cls, table: symtable.SymbolTable) -> LexicalBindings:
        """Use the public CPython classifier rather than another lexical parser."""
        symbols = table.get_symbols()
        return cls(
            frozenset(item.get_name() for item in symbols if item.is_local()),
            frozenset(item.get_name() for item in symbols if item.is_global()),
            frozenset(item.get_name() for item in symbols if item.is_nonlocal()),
            frozenset(
                item.get_name()
                for item in symbols
                if item.is_assigned() and (item.is_global() or item.is_nonlocal())
            ),
            frozenset(item.get_name() for item in symbols if item.is_free()),
        )


@dataclass(slots=True)
class NativeScopes:
    """Invocation-local native lexical classification, not a second parser or graph."""

    tables: dict[tuple[str, int], list[LexicalBindings]]
    sites: dict[ast.AST, LexicalBindings] = field(default_factory=dict)

    @classmethod
    def from_source(cls, source: str, path: str) -> NativeScopes:
        """Classify original source with the current language's native symbol table."""
        tables: dict[tuple[str, int], list[LexicalBindings]] = {}
        pending = [symtable.symtable(source, path, "exec")]
        while pending:
            table = pending.pop()
            key = table.get_name(), table.get_lineno()
            tables.setdefault(key, []).append(LexicalBindings.from_table(table))
            pending.extend(reversed(table.get_children()))
        return cls(tables)

    def for_node(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | ast.ClassDef
    ) -> LexicalBindings:
        """Bind the definition site, including distinct same-line lambda scopes."""
        if node in self.sites:
            return self.sites[node]
        name = "lambda" if isinstance(node, ast.Lambda) else node.name
        candidates = self.tables.get((name, node.lineno), [])
        if not candidates:
            message = "native_scope_unavailable"
            raise ValueError(message)
        binding = candidates.pop(0)
        self.sites[node] = binding
        return binding


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


def complete_python_tree(text: str) -> ast.Module | None:
    """Require native compilation validity without executing the parsed carrier."""
    try:
        tree = _parse_without_syntax_warnings(text)
        with warnings.catch_warnings():
            warnings.simplefilter("error", SyntaxWarning)
            compile(tree, "<reference-carrier>", "exec", dont_inherit=True)
    except (SyntaxError, SyntaxWarning, ValueError):
        return None
    else:
        return tree


def _parse_without_syntax_warnings(text: str) -> ast.Module:
    """Treat warning-producing snippets as invalid partial Python syntax."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", SyntaxWarning)
        return ast.parse(text)


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


def plain_method_class(node: ast.ClassDef, required: frozenset[str]) -> bool:
    """An ordinary class of undecorated methods that defines one of the required names."""
    return (
        not (node.bases or node.decorator_list or node.keywords)
        and all(
            (isinstance(item, ast.FunctionDef) and not item.decorator_list)
            or (isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant))
            for item in node.body
        )
        and any(getattr(item, "name", "") in required for item in node.body)
    )
