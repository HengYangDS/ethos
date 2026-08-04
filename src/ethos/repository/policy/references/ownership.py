"""Positive reference ownership compiled from native repository carriers."""

from __future__ import annotations

import json
import re
import shlex
import sys
import tomllib
from collections import defaultdict
from typing import TYPE_CHECKING

import yaml

import ethos.repository.policy.references.commands as command_references
import ethos.repository.policy.references.python_syntax as python_references
from ethos.repository.policy.boundary.product import product_surface_files
from ethos.repository.policy.references.commands import normalize_command

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def native_owned_references(root: Path) -> dict[str, frozenset[str]]:
    """Compile admitted identities from native declarations, never consumers."""
    return native_owned_references_from_files(_repository_files(root))


def native_owned_references_from_files(
    files: dict[str, str],
) -> dict[str, frozenset[str]]:
    """Compile the positive closure from package, command, tool, and profile owners."""
    owned = {kind: set() for kind in _REFERENCE_KINDS}
    npm_scripts = _npm_scripts(files, root=None)
    mappings, first_party = _python_import_owners(files)
    for path, text in files.items():
        if path.endswith("pyproject.toml"):
            before = set(owned["distribution"])
            _pyproject_references(text, owned)
            owned["import"].update(
                mappings.get(name, name.replace("-", "_"))
                for name in owned["distribution"] - before
                if not name.startswith("@")
            )
        elif path.endswith("package.json"):
            _package_json_references(text, npm_scripts, owned, declarations=True)
    owned["import"].update(first_party)
    _declared_commands(files, owned)
    _declared_gates(files, npm_scripts, owned)
    _declared_tools(files, owned)
    _declared_profiles(files, owned)
    return {kind: frozenset(owned[kind]) for kind in _REFERENCE_KINDS}


def _python_import_owners(files: dict[str, str]) -> tuple[dict[str, str], set[str]]:
    payload = _toml(files.get(".config/checks/deptry/policy.toml", ""))
    mappings: dict[str, str] = {}
    first_party = set()
    for package in _table_items(payload.get("package")):
        first_party.update(_string_items(package.get("known_first_party")))
        for item in _string_items(package.get("package_module_name_map")):
            distribution, separator, module = item.partition("=")
            if separator and distribution and module:
                mappings[_normalized_distribution(distribution)] = module
    return mappings, first_party


def _declared_commands(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    sources = {path: text for path, text in files.items() if path.endswith(".py")}
    prefixes = python_references.cyclopts_prefixes(sources)
    owned["command"].update(prefixes.values())
    for path, text in sources.items():
        for tree in python_references.python_trees(text):
            owned["command"].update(python_references.cyclopts_commands(path, tree, prefixes))


def _declared_gates(
    files: dict[str, str],
    npm_scripts: dict[str, set[str]],
    owned: dict[str, set[str]],
) -> None:
    payload = _toml(files.get("system/gates.toml", ""))
    for gate in _table_items(payload.get("gates")):
        command = tuple(_string_items(gate.get("command")))
        owned["executable"].update(command_references.command_executables(command, npm_scripts))


def _declared_tools(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    payload = _toml(files.get("system/tools.toml", ""))
    for tool in _table_items(payload.get("tool")):
        for field, kind in (
            ("executables", "executable"),
            ("references", "reference"),
            ("runtime_inputs", "value"),
        ):
            owned[kind].update(_string_items(tool.get(field)))


def _declared_profiles(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    _declared_profile_capabilities(files, owned)
    _declared_surface_inputs(files, owned)
    _declared_release_references(files, owned)
    _declared_provider_references(files, owned)


def _declared_profile_capabilities(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    profile = _toml(files.get(".ethos/profile.toml", ""))
    if isinstance(profile.get("openspec"), dict):
        owned["executable"].add("openspec")
    release = _toml(files.get(".ethos/release.toml", ""))
    attestation = release.get("attestation", {}) if isinstance(release, dict) else {}
    if isinstance(attestation, dict) and attestation.get("signing") == "git-ssh":
        owned["executable"].add("ssh-keygen")


def _declared_surface_inputs(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    surfaces = _toml(files.get("system/surfaces.toml", ""))
    runtime = surfaces.get("runtime", {}) if isinstance(surfaces, dict) else {}
    if isinstance(runtime, dict):
        owned["value"].update(_string_items(runtime.get("inputs")))


def _declared_release_references(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    release = _toml(files.get(".ethos/release.toml", ""))
    host = release.get("host_profile", {}) if isinstance(release, dict) else {}
    if isinstance(host, dict) and isinstance(provider := host.get("provider"), str):
        owned["reference"].add(provider)
    publication = release.get("publication", {}) if isinstance(release, dict) else {}
    if isinstance(publication, dict):
        owned["reference"].update(
            key.removesuffix("_remote")
            for key in publication
            if isinstance(key, str) and key.endswith("_remote")
        )


def _declared_provider_references(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    templates = _toml(files.get(".config/checks/ci/templates.toml", ""))
    for section in ("projection", "forge_surface"):
        for entry in _table_items(templates.get(section)):
            if isinstance(provider := entry.get("provider"), str):
                owned["reference"].add(provider)
            if isinstance(tool := entry.get("emulator_tool"), str):
                owned["executable"].add(tool)
            if entry.get("emulator_image"):
                owned["executable"].add("docker")
                owned["reference"].add("docker")


def _toml(text: str) -> dict[str, object]:
    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _string_items(value: object) -> tuple[str, ...]:
    return tuple(item for item in value if isinstance(item, str)) if isinstance(value, list) else ()


def _table_items(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list):
        return ()
    tables: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, dict):
            tables.append({str(key): entry for key, entry in item.items()})
    return tuple(tables)


def _repository_files(root: Path) -> dict[str, str]:
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
    return files


def product_reference_gaps(
    allowed: dict[str, frozenset[str]],
    observed: dict[str, set[str]],
) -> list[str]:
    """Reject machine references outside one declared product closure."""
    return _reference_gaps(allowed, observed)


def repository_product_reference_gaps(root: Path) -> list[str]:
    """Return references without a positive native owner."""
    allowed = native_owned_references(root)
    observed = product_references_from_files(
        _repository_files(root), root=root, include_declarations=False
    )
    return _reference_gaps(allowed, observed)


def repository_product_references(root: Path) -> dict[str, set[str]]:
    """Observe typed machine references across active product surfaces."""
    return product_references_from_files(_repository_files(root), root=root)


def product_references_from_files(
    files: dict[str, str],
    *,
    root: Path | None = None,
    declared_commands: Iterable[str] = (),
    include_declarations: bool = True,
) -> dict[str, set[str]]:
    """Observe typed references from complete files."""
    declared_commands = tuple(declared_commands)
    command_sources = _command_source_files(files, root=root)
    prefixes = python_references.cyclopts_prefixes(command_sources)
    known_commands = {
        normalize_command(command) for command in declared_commands if command.strip()
    }
    for path, text in command_sources.items():
        for tree in python_references.python_trees(text):
            known_commands.update(python_references.cyclopts_commands(path, tree, prefixes))
    npm_scripts = _npm_scripts(command_sources, root=root)
    observed = {kind: set() for kind in _REFERENCE_KINDS}
    for path, text in files.items():
        _file_references(
            path,
            text,
            prefixes,
            known_commands,
            npm_scripts,
            observed,
            include_declarations=include_declarations,
        )
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


def _file_references(
    path: str,
    text: str,
    prefixes: dict[tuple[str, str], str],
    known_commands: set[str],
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    *,
    include_declarations: bool,
) -> None:
    suffix = path.rpartition(".")[2].lower()
    if suffix == "py":
        _python_file_references(path, text, prefixes, npm_scripts, observed)
        return
    if path.endswith("pyproject.toml"):
        if include_declarations:
            _pyproject_references(text, observed)
        return
    if path.endswith("package.json"):
        _package_json_references(text, npm_scripts, observed, declarations=include_declarations)
        return
    if suffix in {"yaml", "yml"}:
        _yaml_references(path, text, npm_scripts, observed)
    elif suffix == "sh":
        observed["executable"].update(command_references.shell_executables(text, npm_scripts))
    elif suffix == "md":
        _markdown_references(path, text, known_commands, npm_scripts, observed)
    if text.startswith("#!") and (
        executable := command_references.shebang_executable(text.splitlines()[0])
    ):
        observed["executable"].add(executable)


def _python_file_references(
    path: str,
    text: str,
    prefixes: dict[tuple[str, str], str],
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
) -> None:
    for tree in python_references.python_trees(text):
        observed["import"].update(python_references.import_roots(tree))
        if path.startswith("tests/"):
            continue
        observed["executable"].update(python_references.python_executables(tree, npm_scripts))
        observed["value"].update(python_references.runtime_inputs(tree))
        observed["command"].update(python_references.cyclopts_commands(path, tree, prefixes))


def _pyproject_references(text: str, observed: dict[str, set[str]]) -> None:
    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
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
            names.add(_normalized_distribution(match.group(0)))
    return names


def _normalized_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


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
    text: str,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    *,
    declarations: bool,
) -> None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return
    if declarations:
        _package_json_declarations(payload, observed)
    for command in payload.get("scripts", {}).values():
        if isinstance(command, str):
            observed["executable"].update(
                command_references.shell_executables(command, npm_scripts)
            )


def _package_json_declarations(payload: dict[str, object], observed: dict[str, set[str]]) -> None:
    if payload.get("private") is not True and isinstance(name := payload.get("name"), str):
        observed["distribution"].add(name.lower())
    for field in (
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
    ):
        values = payload.get(field, {})
        if isinstance(values, dict):
            observed["distribution"].update(str(name).lower() for name in values)
    if isinstance(manager := payload.get("packageManager"), str):
        observed["executable"].add(manager.partition("@")[0])
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
                observed["executable"].update(
                    command_references.shell_executables(command, npm_scripts)
                )
    elif key == "image" and isinstance(item, str) and item:
        observed["reference"].add("docker")


def _github_reference(value: str) -> str:
    action = value.strip().strip("'\"")
    if not action or action.startswith("./"):
        return ""
    if action.startswith("docker://"):
        return "docker"
    return "github" if "@" in action and "/" in action.partition("@")[0] else ""


def _markdown_references(
    path: str,
    text: str,
    known_commands: set[str],
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
) -> None:
    require_declared = _requires_declared_commands(path)
    for match in _MARKDOWN_FENCE.finditer(text):
        language = match.group("language").lower()
        body = match.group("body")
        if language in {"bash", "console", "sh", "shell", "zsh"}:
            shell = (
                "\n".join(
                    line.lstrip()[2:]
                    for line in body.splitlines()
                    if line.lstrip().startswith(("$ ", "> "))
                )
                if language == "console"
                else body
            )
            observed["executable"].update(command_references.shell_executables(shell, npm_scripts))
            observed["command"].update(
                command_references.shell_commands(
                    shell,
                    known_commands,
                    require_declared=require_declared,
                )
            )
        elif language in {"yaml", "yml"}:
            _yaml_references(path, body, npm_scripts, observed)
    for inline in _MARKDOWN_INLINE_CODE.findall(text):
        try:
            tokens = tuple(shlex.split(inline))
        except ValueError:
            continue
        if command := command_references.command_identity(
            tokens,
            known_commands,
            require_declared=require_declared,
        ):
            observed["command"].add(command)
            observed["executable"].update(
                command_references.command_executables(tokens, npm_scripts)
            )


def _requires_declared_commands(path: str) -> bool:
    if path in {"AGENTS.md", "CONTRIBUTING.md", "README.md", "docs/README.md", "docs/index.md"}:
        return True
    return path.startswith(
        (
            ".agents/skills/",
            ".config/forge/",
            ".github/ISSUE_TEMPLATE/",
            ".gitlab/issue_templates/",
            "docs/architecture/",
            "docs/concepts/",
            "docs/governance/",
            "docs/reference/",
            "docs/start/",
            "rules/",
        )
    )


def _reference_gaps(
    allowed: dict[str, frozenset[str]],
    observed: dict[str, set[str]],
) -> list[str]:
    gaps = []
    for kind in _REFERENCE_KINDS:
        for reference in sorted(observed.get(kind, set()) - set(allowed.get(kind, ()))):
            if kind == "import" and reference in {"ethos", "tests", "tools"}:
                continue
            gaps.append(f"product_reference_not_admitted_at_baseline:{kind}:{reference}")
    return gaps


_REFERENCE_KINDS = ("import", "distribution", "executable", "reference", "command", "value")
_REFERENCE_FILE_SUFFIXES = {".json", ".md", ".mjs", ".py", ".sh", ".toml", ".yaml", ".yml"}
_MARKDOWN_FENCE = re.compile(
    r"^```(?P<language>[A-Za-z0-9_-]+)[^\n]*\n(?P<body>.*?)^```\s*$",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
_MARKDOWN_INLINE_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
