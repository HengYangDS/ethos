"""Positive product-binding closure extraction and validation."""

from __future__ import annotations

import ast
import json
import re
import shlex
import sys
import tomllib
from collections import defaultdict
from typing import TYPE_CHECKING

import yaml

from ethos.adapters.repo.git import committed_file_text
from ethos.contracts.registry.declarations import CouplingDeclaration
from ethos.contracts.registry.declarations import load_coupling_declaration
from ethos.contracts.registry.declarations import normalize_binding_command
from ethos.repository.policy.boundary.product import product_surface_files

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def baseline_product_references(root: Path, head: str) -> dict[str, frozenset[str]]:
    """Return external references admitted by the binding declaration at ``head``."""
    text = committed_file_text(root, head, "system/coupling.toml")
    try:
        declaration = CouplingDeclaration.model_validate(tomllib.loads(text))
    except (tomllib.TOMLDecodeError, ValueError):
        return {kind: frozenset() for kind in _REFERENCE_KINDS}
    return declared_product_references(declaration)


def declared_product_references(
    declaration: CouplingDeclaration,
) -> dict[str, frozenset[str]]:
    """Return the typed reference closure of one validated binding declaration."""
    values: dict[str, set[str]] = {kind: set() for kind in _REFERENCE_KINDS}
    for binding in declaration.bindings:
        if binding.distribution:
            values["distribution"].add(binding.distribution)
        values["import"].update(binding.import_roots)
        values["executable"].update(binding.executables)
        values["reference"].update(binding.references)
        values["command"].update(normalize_binding_command(command) for command in binding.commands)
    return {kind: frozenset(items) for kind, items in values.items()}


def latent_product_references(
    declaration: CouplingDeclaration,
) -> dict[str, frozenset[str]]:
    """Return explicitly justified declaration identities absent from current surfaces."""
    values: dict[str, set[str]] = {kind: set() for kind in _REFERENCE_KINDS}
    for binding in declaration.bindings:
        latent = binding.latent
        if latent is None:
            continue
        if latent.distribution:
            values["distribution"].add(latent.distribution)
        values["import"].update(latent.import_roots)
        values["executable"].update(latent.executables)
        values["reference"].update(latent.references)
        values["command"].update(normalize_binding_command(value) for value in latent.commands)
    return {kind: frozenset(items) for kind, items in values.items()}


def product_reference_gaps(
    root: Path,
    head: str,
    observed: dict[str, set[str]],
) -> list[str]:
    """Reject machine references not admitted by the baseline product declaration."""
    allowed = baseline_product_references(root, head)
    return _reference_gaps(allowed, observed)


def repository_product_reference_gaps(root: Path) -> list[str]:
    """Return machine references outside the positive product binding closure."""
    declaration = load_coupling_declaration(root / "system/coupling.toml")
    allowed = declared_product_references(declaration)
    return _reference_gaps(
        allowed,
        repository_product_references(root, declaration=declaration),
        latent=latent_product_references(declaration),
        symmetric=True,
    )


def repository_product_references(
    root: Path, *, declaration: CouplingDeclaration | None = None
) -> dict[str, set[str]]:
    """Observe typed machine references across active product surfaces."""
    paths = set(product_surface_files(root))
    for relative in (".agents/skills", "src/ethos", "tests", "tools"):
        base = root / relative
        if base.exists():
            paths.update(
                path
                for path in base.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix in _REFERENCE_FILE_SUFFIXES
            )
    files = {}
    for path in sorted(paths):
        try:
            files[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
    return product_references_from_files(
        files,
        root=root,
        declared_commands=(
            declared_product_references(declaration)["command"] if declaration is not None else ()
        ),
    )


def product_references_from_files(
    files: dict[str, str],
    *,
    root: Path | None = None,
    declared_commands: Iterable[str] = (),
) -> dict[str, set[str]]:
    """Observe the five binding kinds from complete files."""
    declared_commands = _declared_command_identities(root, tuple(declared_commands))
    command_sources = _command_source_files(files, root=root)
    prefixes = _cyclopts_prefixes(command_sources)
    known_commands = {
        normalize_binding_command(command) for command in declared_commands if command.strip()
    }
    for path, text in command_sources.items():
        for tree in _python_trees(text):
            known_commands.update(_cyclopts_commands(path, tree, prefixes))
    npm_scripts = _npm_scripts(command_sources, root=root)
    observed = {kind: set() for kind in _REFERENCE_KINDS}
    for path, text in files.items():
        _file_references(path, text, prefixes, known_commands, npm_scripts, observed)
    observed["import"].difference_update(sys.stdlib_module_names)
    return observed


def _command_source_files(files: dict[str, str], *, root: Path | None) -> dict[str, str]:
    command_sources = dict(files)
    if root is None:
        return command_sources
    for base in (root / "src", root / "tools"):
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            if "App(" in text:
                command_sources.setdefault(path.relative_to(root).as_posix(), text)
    return command_sources


def _declared_command_identities(
    root: Path | None, declared_commands: tuple[str, ...]
) -> tuple[str, ...]:
    if declared_commands or root is None:
        return declared_commands
    path = root / "system/coupling.toml"
    if not path.is_file():
        return ()
    declaration = load_coupling_declaration(path)
    return tuple(declared_product_references(declaration)["command"])


def _file_references(
    path: str,
    text: str,
    prefixes: dict[tuple[str, str], str],
    known_commands: set[str],
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
) -> None:
    suffix = path.rpartition(".")[2].lower()
    if suffix == "py":
        for tree in _python_trees(text):
            observed["import"].update(_import_roots(tree))
            if not path.startswith("tests/"):
                observed["executable"].update(_python_executables(tree, npm_scripts))
            observed["command"].update(_cyclopts_commands(path, tree, prefixes))
    elif path.endswith("pyproject.toml"):
        _pyproject_references(text, observed)
    elif path.endswith("package.json"):
        _package_json_references(text, npm_scripts, observed)
    elif suffix in {"yaml", "yml"}:
        _yaml_references(path, text, npm_scripts, observed)
    elif suffix == "sh":
        observed["executable"].update(_shell_executables(text, npm_scripts))
    elif suffix == "md":
        _markdown_references(path, text, known_commands, npm_scripts, observed)
    if text.startswith("#!") and (executable := _shebang_executable(text.splitlines()[0])):
        observed["executable"].add(executable)


def _python_trees(text: str) -> tuple[ast.AST, ...]:
    try:
        return (ast.parse(text),)
    except SyntaxError:
        trees = []
        for line in text.splitlines():
            candidate = line
            if line.lstrip().startswith("@"):
                candidate += "\ndef _binding_probe() -> None:\n    pass"
            try:
                trees.append(ast.parse(candidate))
            except SyntaxError:
                continue
        return tuple(trees)


def _import_roots(tree: ast.AST) -> set[str]:
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _python_executables(tree: ast.AST, npm_scripts: dict[str, set[str]]) -> set[str]:
    executables = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            executables.update(_call_executables(node, npm_scripts))
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if (
                isinstance(target, ast.Name)
                and re.search(r"(?:COMMAND|CMD|EXECUTABLE|BINARY|CLI|TOOL)$", target.id)
                and isinstance(node.value, ast.List | ast.Tuple)
            ):
                executables.update(
                    _command_executables(_literal_command_tokens(node.value), npm_scripts)
                )
    return executables


def _call_executables(node: ast.Call, npm_scripts: dict[str, set[str]]) -> set[str]:
    name = node.func.id if isinstance(node.func, ast.Name) else ""
    attribute = node.func.attr if isinstance(node.func, ast.Attribute) else ""
    owner = (
        node.func.value.id
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
        else ""
    )
    if node.args and (owner == "subprocess" and attribute in _SUBPROCESS_CALLS):
        return _command_executables(_literal_command_tokens(node.args[0]), npm_scripts)
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


def _cyclopts_prefixes(files: dict[str, str]) -> dict[tuple[str, str], str]:
    prefixes: dict[tuple[str, str], str] = {}
    for path, text in files.items():
        if "App(" not in text:
            continue
        trees = _python_trees(text)
        if not trees:
            continue
        tree = trees[0]
        names = {
            target.id: _app_name(node.value, target.id)
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance((target := node.targets[0]), ast.Name)
            and _is_app(node.value)
        }
        parents = {
            node.args[0].id: node.func.value.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "command"
            and isinstance(node.func.value, ast.Name)
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in names
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.For) or not isinstance(node.iter, ast.Tuple | ast.List):
                continue
            parent = next(
                (
                    call.func.value.id
                    for call in ast.walk(node)
                    if isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "command"
                    and isinstance(call.func.value, ast.Name)
                ),
                "",
            )
            parents.update(
                {
                    item.id: parent
                    for item in node.iter.elts
                    if parent and isinstance(item, ast.Name)
                }
            )

        module = _module_name(path)
        prefixes.update(
            {
                (module, name): _resolve_app_prefix(name, names=names, parents=parents)
                for name in names
            }
        )
    return prefixes


def _resolve_app_prefix(
    name: str,
    *,
    names: dict[str, str],
    parents: dict[str, str],
    trail: frozenset[str] = frozenset(),
) -> str:
    if name in trail or name not in names:
        return ""
    parent = (
        _resolve_app_prefix(parents[name], names=names, parents=parents, trail=trail | {name})
        if name in parents
        else ""
    )
    return " ".join(part for part in (parent, names[name]) if part)


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


def _module_name(path: str) -> str:
    parts = path.removeprefix("src/").removesuffix(".py").split("/")
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _import_module(path: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    package = _module_name(path).split(".")[: -node.level]
    return ".".join((*package, *((node.module or "").split("."))))


def _cyclopts_commands(path: str, tree: ast.AST, prefixes: dict[tuple[str, str], str]) -> set[str]:
    imported = {
        alias.asname or alias.name: (_import_module(path, node), alias.name)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    commands = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            owner, names = _command_names(decorator, node.name)
            key = imported.get(owner, (_module_name(path), owner))
            prefix = prefixes.get(key, "")
            if not prefix:
                candidates = {value for (_, name), value in prefixes.items() if name == owner}
                prefix = candidates.pop() if len(candidates) == 1 else ""
            commands.update(
                normalize_binding_command(" ".join(part for part in (prefix, name) if part))
                for name in names
            )
    return commands


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


def _pyproject_references(text: str, observed: dict[str, set[str]]) -> None:
    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        observed["distribution"].update(_requirement_names(text.splitlines()))
        return
    project = payload.get("project", {})
    if isinstance(project, dict):
        if isinstance(name := project.get("name"), str):
            observed["distribution"].update(_requirement_names([name]))
        observed["distribution"].update(_requirement_names(project.get("dependencies", [])))
        for values in project.get("optional-dependencies", {}).values():
            observed["distribution"].update(_requirement_names(values))
        observed["executable"].update(project.get("scripts", {}))
    for values in payload.get("dependency-groups", {}).values():
        observed["distribution"].update(_requirement_names(values))
    observed["distribution"].update(
        _requirement_names(payload.get("build-system", {}).get("requires", []))
    )


def _requirement_names(values: object) -> set[str]:
    names = set()
    if not isinstance(values, list | tuple):
        return names
    for value in values:
        match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) if isinstance(value, str) else None
        if match:
            names.add(re.sub(r"[-_.]+", "-", match.group(0)).lower())
    return names


def _npm_scripts(files: dict[str, str], *, root: Path | None) -> dict[str, set[str]]:
    manifests: dict[str, str] = {}
    if root is not None:
        for path in product_surface_files(root):
            if path.name != "package.json":
                continue
            try:
                manifests[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
    manifests.update({path: text for path, text in files.items() if path.endswith("package.json")})
    scripts: dict[str, set[str]] = defaultdict(set)
    for text in manifests.values():
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        values = payload.get("scripts", {}) if isinstance(payload, dict) else {}
        if not isinstance(values, dict):
            continue
        for name, command in values.items():
            if isinstance(name, str) and isinstance(command, str):
                scripts[name].add(command)
    return dict(scripts)


def _package_json_references(
    text: str, npm_scripts: dict[str, set[str]], observed: dict[str, set[str]]
) -> None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return
    if payload.get("private") is not True and isinstance(name := payload.get("name"), str):
        observed["distribution"].add(name.lower())
    for field in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        values = payload.get(field, {})
        if isinstance(values, dict):
            observed["distribution"].update(str(name).lower() for name in values)
    if isinstance(manager := payload.get("packageManager"), str):
        observed["executable"].add(manager.partition("@")[0])
    for command in payload.get("scripts", {}).values():
        if isinstance(command, str):
            observed["executable"].update(_shell_executables(command, npm_scripts))
    if isinstance(bins := payload.get("bin"), dict):
        observed["executable"].update(str(name) for name in bins)


def _yaml_references(
    path: str,
    text: str,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
) -> None:
    if path.startswith(".github/"):
        observed["reference"].add("github")
    elif path == ".gitlab-ci.yml" or path.startswith(".gitlab/"):
        observed["reference"].add("gitlab")
    try:
        stack = [yaml.safe_load(text)]
    except yaml.YAMLError:
        stack = []
    while stack:
        value = stack.pop()
        if isinstance(value, list):
            stack.extend(value)
        elif isinstance(value, dict):
            stack.extend(value.values())
            for key, item in value.items():
                _configuration_reference(str(key), item, npm_scripts, observed)


def _configuration_reference(
    key: str,
    item: object,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
) -> None:
    if key == "uses" and isinstance(item, str):
        if reference := _github_reference(item):
            observed["reference"].add(reference)
    elif key in {"run", "script"}:
        commands = item if isinstance(item, list) else [item]
        for command in commands:
            if isinstance(command, str):
                observed["executable"].update(_shell_executables(command, npm_scripts))
    elif key == "image" and isinstance(item, str) and item:
        observed["reference"].add("docker")


def _github_reference(value: str) -> str:
    action = value.strip().strip("'\"")
    if not action or action.startswith("./"):
        return ""
    if action.startswith("docker://"):
        return "docker"
    return "github" if "@" in action and "/" in action.partition("@")[0] else ""


def _shell_executables(text: str, npm_scripts: dict[str, set[str]]) -> set[str]:
    functions = {
        match.group(1)
        for line in text.splitlines()
        if (match := re.match(r"\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\)\s*\{", line))
    }
    executables = set()
    for line in _shell_candidate_lines(text):
        for tokens in _shell_command_segments(line):
            values = _command_executables(tokens, npm_scripts)
            executables.update(value for value in values if value not in functions)
    return executables


def _shell_candidate_lines(text: str) -> list[str]:
    lines = []
    heredoc = ""
    array_depth = 0
    for raw in text.splitlines():
        line = raw.strip()
        if heredoc:
            heredoc = "" if line == heredoc else heredoc
            continue
        if array_depth:
            array_depth += line.count("(") - line.count(")")
            continue
        if re.match(r"[A-Za-z_]\w*=\(", line):
            array_depth = line.count("(") - line.count(")")
            continue
        if match := re.search(r"<<-?\s*['\"]?([A-Za-z_]\w*)['\"]?", line):
            heredoc, line = match.group(1), line[: match.start()].rstrip()
        if line := _shell_command_line(line):
            lines.append(line)
    return lines


def _shell_command_segments(line: str) -> tuple[tuple[str, ...], ...]:
    lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split, lexer.commenters = True, "#"
    try:
        tokens = list(lexer)
    except ValueError:
        return ()
    segments: list[tuple[str, ...]] = []
    start = 0
    for index, token in enumerate((*tokens, ";")):
        if token not in _SHELL_SEPARATORS:
            continue
        segment = tuple(tokens[start:index])
        start = index + 1
        command = _shell_segment_command(segment)
        if command:
            segments.append(command)
    return tuple(segments)


def _shell_segment_command(tokens: tuple[str, ...]) -> tuple[str, ...]:
    for index, token in enumerate(tokens):
        if _ignored_shell_token(token):
            continue
        if token in _SHELL_NON_EXECUTABLES or token.startswith("$"):
            return ()
        return tokens[index:]
    return ()


def _command_executables(
    tokens: tuple[str, ...],
    npm_scripts: dict[str, set[str]],
    *,
    trail: frozenset[str] = frozenset(),
) -> set[str]:
    command = _command_tokens(tokens)
    if not command or not (executable := _executable_identity(command[0])):
        return set()
    executables = {executable}
    child = _wrapped_command_tokens(command, executable)
    if child:
        executables.update(_command_executables(child, npm_scripts, trail=trail))
    if executable == "npm" and (script := _npm_script_name(command)) and script not in trail:
        for value in npm_scripts.get(script, set()):
            try:
                script_tokens = tuple(shlex.split(value))
            except ValueError:
                continue
            executables.update(
                _command_executables(script_tokens, npm_scripts, trail=trail | {script})
            )
    return executables


def _command_tokens(tokens: tuple[str, ...]) -> tuple[str, ...]:
    for index, argument in enumerate(tokens):
        if (
            argument in _SHELL_PREFIXES
            or argument in {"(", ")"}
            or _SHELL_ASSIGNMENT.fullmatch(argument)
        ):
            continue
        if argument.startswith("-") or argument.isdigit():
            continue
        return tokens[index:]
    return ()


def _wrapped_command_tokens(tokens: tuple[str, ...], executable: str) -> tuple[str, ...]:
    if executable == "uv":
        run_index = next(
            (index for index, argument in enumerate(tokens[1:], 1) if argument == "run"), -1
        )
        return (
            _tokens_after_options(tokens[run_index + 1 :], _UV_RUN_OPTIONS_WITH_VALUE)
            if run_index >= 0
            else ()
        )
    if executable in {"python", "python3"} or re.fullmatch(r"python\d+(?:\.\d+)*", executable):
        module_index = next(
            (index for index, argument in enumerate(tokens[1:], 1) if argument == "-m"), -1
        )
        return tokens[module_index + 1 : module_index + 2] if module_index >= 0 else ()
    if executable in {"npx", "uvx"}:
        value_options = _NPX_OPTIONS_WITH_VALUE if executable == "npx" else _UVX_OPTIONS_WITH_VALUE
        child = _tokens_after_options(tokens[1:], value_options)
        package_command = _package_command(child[0]) if child else ""
        return (package_command, *child[1:]) if package_command else ()
    return ()


def _tokens_after_options(
    tokens: tuple[str, ...], options_with_value: frozenset[str]
) -> tuple[str, ...]:
    index = 0
    while index < len(tokens):
        argument = tokens[index]
        if argument.startswith((">", "<")):
            return ()
        if argument == "--":
            return tokens[index + 1 :]
        if not argument.startswith("-"):
            return tokens[index:]
        option = argument.partition("=")[0]
        index += 2 if option in options_with_value and "=" not in argument else 1
    return ()


def _package_command(argument: str) -> str:
    package = argument
    if package.startswith("@") and "/" in package:
        package, separator, _ = package.rpartition("@")
        package = package if separator else argument
    elif "@" in package:
        package = package.partition("@")[0]
    return package.rsplit("/", maxsplit=1)[-1]


def _npm_script_name(tokens: tuple[str, ...]) -> str:
    args = _tokens_after_options(tokens[1:], _NPM_OPTIONS_WITH_VALUE)
    if not args or args[0] not in {"run", "run-script"}:
        return ""
    script = _tokens_after_options(args[1:], _NPM_OPTIONS_WITH_VALUE)
    return script[0] if script else ""


def _executable_identity(token: str) -> str:
    if token.startswith("/dev/"):
        return ""
    if token.startswith("/"):
        token = token.rsplit("/", maxsplit=1)[-1]
    elif "/" in token:
        return ""
    return token if re.fullmatch(r"[A-Za-z0-9_.+-]+", token) else ""


def _shell_command_line(line: str) -> str:
    if (
        not line
        or line.startswith(("#", "-", "for ((", "case "))
        or re.match(r"(?:function\s+)?\w+\s*\(\)\s*\{", line)
    ):
        return ""
    if match := re.match(r"[A-Za-z0-9_*-]+(?:\|[A-Za-z0-9_*-]+)*\)\s*(.*)$", line):
        line = match.group(1)
    return line.removeprefix("$").lstrip()


def _ignored_shell_token(token: str) -> bool:
    return bool(
        _SHELL_ASSIGNMENT.fullmatch(token)
        or token.startswith("-")
        or token.isdigit()
        or token in _SHELL_PREFIXES
    )


def _shebang_executable(line: str) -> str:
    try:
        tokens = shlex.split(line.removeprefix("#!"))
    except ValueError:
        return ""
    if not tokens:
        return ""
    executable = tokens[0].rsplit("/", maxsplit=1)[-1]
    return tokens[1] if executable == "env" and len(tokens) > 1 else executable


def _markdown_references(
    path: str,
    text: str,
    known_commands: set[str],
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
) -> None:
    for match in _MARKDOWN_FENCE.finditer(text):
        language = match.group("language").lower()
        body = match.group("body")
        if language in {"bash", "console", "sh", "shell", "zsh"}:
            shell = _console_commands(body) if language == "console" else body
            observed["executable"].update(_shell_executables(shell, npm_scripts))
            observed["command"].update(_shell_commands(shell, known_commands))
        elif language in {"yaml", "yml"}:
            _yaml_references(path, body, npm_scripts, observed)
    for inline in _MARKDOWN_INLINE_CODE.findall(text):
        try:
            tokens = tuple(shlex.split(inline))
        except ValueError:
            continue
        if command := _command_identity(tokens, known_commands):
            observed["command"].add(command)
            observed["executable"].update(_command_executables(tokens, npm_scripts))


def _console_commands(text: str) -> str:
    return "\n".join(
        line.lstrip()[2:] for line in text.splitlines() if line.lstrip().startswith(("$ ", "> "))
    )


def _shell_commands(text: str, known_commands: set[str]) -> set[str]:
    return {
        command
        for line in _shell_candidate_lines(text)
        for tokens in _shell_command_segments(line)
        if (command := _command_identity(tokens, known_commands))
    }


def _command_identity(tokens: tuple[str, ...], known_commands: set[str]) -> str:
    command = _command_tokens(tokens)
    if not command:
        return ""
    executable = _executable_identity(command[0])
    child = _wrapped_command_tokens(command, executable)
    if child:
        return _command_identity(child, known_commands)
    candidates = []
    for known in known_commands:
        try:
            known_tokens = tuple(shlex.split(known))
        except ValueError:
            continue
        if command[: len(known_tokens)] == known_tokens:
            candidates.append((len(known_tokens), known))
    if candidates:
        return max(candidates)[1]
    return ""


def _reference_gaps(
    allowed: dict[str, frozenset[str]],
    observed: dict[str, set[str]],
    *,
    latent: dict[str, frozenset[str]] | None = None,
    symmetric: bool = False,
) -> list[str]:
    gaps: list[str] = []
    latent = latent or {kind: frozenset() for kind in _REFERENCE_KINDS}
    for kind in _REFERENCE_KINDS:
        for reference in sorted(observed.get(kind, set()) - set(allowed[kind])):
            if kind == "import" and reference in {"ethos", "tests", "tools"}:
                continue
            gaps.append(f"product_reference_not_admitted_at_baseline:{kind}:{reference}")
        if symmetric:
            declared_only = set(allowed[kind]) - observed.get(kind, set()) - set(latent[kind])
            gaps.extend(
                f"product_reference_declared_but_unobserved:{kind}:{reference}"
                for reference in sorted(declared_only)
            )
    return gaps


_REFERENCE_KINDS = ("import", "distribution", "executable", "reference", "command")
_REFERENCE_FILE_SUFFIXES = {".json", ".md", ".mjs", ".py", ".sh", ".toml", ".yaml", ".yml"}
_SUBPROCESS_CALLS = {"run", "Popen", "check_call", "check_output"}
_SHELL_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
_SHELL_SEPARATORS = {"&", "&&", ";", ";;", "|", "||"}
_SHELL_PREFIXES = {
    "!",
    "command",
    "do",
    "elif",
    "else",
    "env",
    "exec",
    "if",
    "sudo",
    "then",
    "time",
}
_SHELL_NON_EXECUTABLES = {
    "[",
    "[[",
    "break",
    "case",
    "cd",
    "continue",
    "declare",
    "done",
    "echo",
    "esac",
    "eval",
    "exit",
    "export",
    "false",
    "fi",
    "for",
    "local",
    "printf",
    "read",
    "readonly",
    "return",
    "set",
    "shift",
    "shopt",
    "source",
    "test",
    "trap",
    "true",
    "typeset",
    "ulimit",
    "umask",
    "unset",
    "until",
    "wait",
    "while",
}
_UV_RUN_OPTIONS_WITH_VALUE = frozenset(
    {
        "--cache-dir",
        "--config-file",
        "--config-setting",
        "--directory",
        "--env-file",
        "--exclude-newer",
        "--group",
        "--index",
        "--link-mode",
        "--package",
        "--project",
        "--python",
        "--resolution",
        "--with",
    }
)
_NPX_OPTIONS_WITH_VALUE = frozenset({"--cache", "--call", "--package", "-c", "-p"})
_UVX_OPTIONS_WITH_VALUE = frozenset(
    {"--from", "--index", "--python", "--refresh-package", "--with"}
)
_NPM_OPTIONS_WITH_VALUE = frozenset({"--prefix", "--workspace", "-w"})
_MARKDOWN_FENCE = re.compile(
    r"^```(?P<language>[A-Za-z0-9_-]+)[^\n]*\n(?P<body>.*?)^```\s*$",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
_MARKDOWN_INLINE_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
