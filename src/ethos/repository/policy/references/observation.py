"""Observe typed product references across repository carriers."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

import ethos.repository.policy.references.commands as command_references
import ethos.repository.policy.references.markdown as markdown_observation
import ethos.repository.policy.references.python_syntax as python_references
from ethos.repository.policy.boundary.product import product_surface_files
from ethos.repository.policy.references.carriers import REFERENCE_KINDS
from ethos.repository.policy.references.carriers import reference_carrier
from ethos.repository.policy.references.carriers import reference_paths
from ethos.repository.policy.references.commands import normalize_command

if TYPE_CHECKING:
    from ast import AST
    from collections.abc import Iterable
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class RepositoryReferenceObservation:
    """One finite read of current reference carriers and unreadable paths."""

    files: dict[str, str]
    unreadable_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReferenceConsumption:
    """Current consumer relation plus carriers whose syntax was not observable."""

    sources: dict[str, dict[str, frozenset[str]]]
    unknown_paths: tuple[str, ...]


def observe_repository_references(root: Path) -> RepositoryReferenceObservation:
    """Read each selected current carrier once and preserve unreadable provenance."""
    files: dict[str, str] = {}
    unreadable_paths: list[str] = []
    for path in reference_paths(root, product_surface_files(root)):
        relative = path.relative_to(root).as_posix()
        try:
            files[relative] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            unreadable_paths.append(relative)
    return RepositoryReferenceObservation(
        files=files,
        unreadable_paths=tuple(sorted(unreadable_paths)),
    )


def product_references_from_files(
    files: dict[str, str],
    *,
    context_files: dict[str, str] | None = None,
    declared_commands: Iterable[str] = (),
    include_declarations: bool = True,
) -> dict[str, set[str]]:
    """Observe typed references from complete files."""
    declared_commands = tuple(declared_commands)
    command_sources = dict(context_files or {})
    command_sources.update(files)
    prefixes = python_references.cyclopts_prefixes(command_sources)
    known_commands = {
        normalize_command(command) for command in declared_commands if command.strip()
    }
    for path, text in command_sources.items():
        for tree in python_references.python_trees(text):
            known_commands.update(python_references.cyclopts_command_owners(path, tree, prefixes))
    command_vocabulary = command_references.CommandVocabulary.compile(known_commands)
    npm_scripts = npm_script_commands(command_sources)
    observed = {kind: set() for kind in REFERENCE_KINDS}
    for path, text in files.items():
        _file_references(
            path,
            text,
            prefixes,
            command_vocabulary,
            npm_scripts,
            observed,
            include_declarations=include_declarations,
        )
    observed["import"].difference_update(sys.stdlib_module_names)
    return observed


def reference_consumer_sources_from_files(
    files: dict[str, str],
    *,
    declared_commands: Iterable[str] = (),
    parsed_files: Mapping[str, AST | None] | None = None,
) -> ReferenceConsumption:
    """Return consumed identities with current carrier provenance."""
    known_commands = {
        normalize_command(command) for command in declared_commands if command.strip()
    }
    command_vocabulary = command_references.CommandVocabulary.compile(known_commands)
    npm_scripts = npm_script_commands(files)
    consumers = {kind: defaultdict(set) for kind in REFERENCE_KINDS}
    unknown_paths: list[str] = []
    for path, text in files.items():
        observed = {kind: set() for kind in REFERENCE_KINDS}
        parsed = _file_references(
            path,
            text,
            {},
            command_vocabulary,
            npm_scripts,
            observed,
            include_declarations=False,
            require_complete=True,
            parsed_files=parsed_files,
        )
        if not parsed:
            unknown_paths.append(path)
            continue
        observed["import"].difference_update(sys.stdlib_module_names)
        for kind, identities in observed.items():
            for identity in identities:
                consumers[kind][identity].add(path)
    return ReferenceConsumption(
        sources={
            kind: {
                identity: frozenset(paths) for identity, paths in sorted(consumers[kind].items())
            }
            for kind in REFERENCE_KINDS
        },
        unknown_paths=tuple(sorted(unknown_paths)),
    )


def _file_references(
    path: str,
    text: str,
    prefixes: dict[tuple[str, str], str],
    known_commands: command_references.CommandVocabulary,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    *,
    include_declarations: bool,
    require_complete: bool = False,
    parsed_files: Mapping[str, AST | None] | None = None,
) -> bool:
    carrier = reference_carrier(path).name
    if carrier == "python":
        return _python_carrier_references(
            path=path,
            text=text,
            prefixes=prefixes,
            npm_scripts=npm_scripts,
            observed=observed,
            include_declarations=include_declarations,
            require_complete=require_complete,
            parsed_files=parsed_files,
        )
    if carrier == "pyproject":
        return _pyproject_carrier_references(
            text,
            observed,
            include_declarations=include_declarations,
            require_complete=require_complete,
        )
    if carrier == "package-json":
        return _package_json_carrier_references(
            text,
            npm_scripts,
            observed,
            include_declarations=include_declarations,
            require_complete=require_complete,
        )
    parsed = _text_carrier_references(
        carrier=carrier,
        path=path,
        text=text,
        known_commands=known_commands,
        npm_scripts=npm_scripts,
        observed=observed,
    )
    if not parsed and require_complete:
        return False
    if text.startswith("#!") and (
        executable := command_references.shebang_executable(text.splitlines()[0])
    ):
        observed["executable"].add(executable)
    return True


def _python_carrier_references(
    *,
    path: str,
    text: str,
    prefixes: dict[tuple[str, str], str],
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    include_declarations: bool,
    require_complete: bool,
    parsed_files: Mapping[str, AST | None] | None,
) -> bool:
    tree = (
        parsed_files.get(path)
        if parsed_files is not None
        else python_references.complete_python_tree(text)
        if require_complete
        else None
    )
    if require_complete and tree is None:
        return False
    _python_file_references(
        path,
        text,
        prefixes,
        npm_scripts,
        observed,
        include_declarations=include_declarations,
        trees=(tree,) if tree is not None else None,
    )
    return True


def _pyproject_carrier_references(
    text: str,
    observed: dict[str, set[str]],
    *,
    include_declarations: bool,
    require_complete: bool,
) -> bool:
    if require_complete and not _valid_toml(text):
        return False
    if include_declarations:
        pyproject_references(text, observed)
    return True


def _package_json_carrier_references(
    text: str,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    *,
    include_declarations: bool,
    require_complete: bool,
) -> bool:
    if require_complete and not _valid_json_object(text):
        return False
    package_json_references(
        text,
        npm_scripts,
        observed,
        declarations=include_declarations,
    )
    return True


def _text_carrier_references(
    *,
    carrier: str,
    path: str,
    text: str,
    known_commands: command_references.CommandVocabulary,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
) -> bool:
    if carrier == "yaml":
        return _yaml_references(path, text, npm_scripts, observed)
    if carrier == "shell":
        observed["executable"].update(command_references.shell_executables(text, npm_scripts))
    elif carrier == "markdown":
        return markdown_observation.markdown_references(
            path,
            text,
            known_commands,
            npm_scripts,
            observed,
            yaml_references=_yaml_references,
        )
    return True


def _python_file_references(
    path: str,
    text: str,
    prefixes: dict[tuple[str, str], str],
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    *,
    include_declarations: bool,
    trees: tuple[AST, ...] | None = None,
) -> None:
    for tree in trees or python_references.python_trees(text):
        imports, executables, inputs = python_references.python_references(tree, npm_scripts)
        observed["import"].update(imports)
        if path.startswith("tests/"):
            continue
        observed["executable"].update(executables)
        observed["value"].update(inputs)
        if include_declarations:
            observed["command"].update(
                python_references.cyclopts_command_owners(path, tree, prefixes)
            )


def pyproject_references(text: str, observed: dict[str, set[str]]) -> None:
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
            names.add(normalized_distribution(match.group(0)))
    return names


def normalized_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def npm_script_commands(files: dict[str, str]) -> dict[str, set[str]]:
    manifests = {
        path: text for path, text in files.items() if reference_carrier(path).name == "package-json"
    }
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


def package_json_references(
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
) -> bool:
    if path.startswith(".github/"):
        observed["reference"].add("github")
    elif path == ".gitlab-ci.yml" or path.startswith(".gitlab/"):
        observed["reference"].add("gitlab")
    try:
        stack = [yaml.safe_load(text)]
    except yaml.YAMLError:
        return False
    while stack:
        value = stack.pop()
        if isinstance(value, list):
            stack.extend(value)
        elif isinstance(value, dict):
            stack.extend(value.values())
            for key, item in value.items():
                _configuration_reference(str(key), item, npm_scripts, observed)
    return True


def _valid_toml(text: str) -> bool:
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return False
    return True


def _valid_json_object(text: str) -> bool:
    try:
        return isinstance(json.loads(text), dict)
    except json.JSONDecodeError:
        return False


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
