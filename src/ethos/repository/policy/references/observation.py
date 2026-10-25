"""Observe typed product references across repository carriers."""

from __future__ import annotations

import importlib.metadata
import inspect
import json
import posixpath
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Literal

import yaml

import ethos.repository.policy.references.commands as command_references
import ethos.repository.policy.references.markdown as markdown_observation
import ethos.repository.policy.references.python_syntax as python_references
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.orchestration import retained_step_texts
from ethos.repository.policy.boundary.product import product_surface_files
from ethos.repository.policy.references.carriers import REFERENCE_KINDS
from ethos.repository.policy.references.carriers import declaration_files
from ethos.repository.policy.references.carriers import reference_carrier
from ethos.repository.policy.references.carriers import reference_paths
from ethos.repository.policy.references.commands import normalize_command
from ethos.repository.policy.references.manifests import normalized_distribution
from ethos.repository.policy.references.manifests import npm_script_commands
from ethos.repository.policy.references.manifests import package_json_references
from ethos.repository.policy.references.manifests import pyproject_references

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


def installed_distribution_modules(root: Path) -> dict[str, tuple[str, ...]]:
    """Map installed distributions to the modules they provide, as native deptry reads them."""
    paths = [
        str(path)
        for pattern in ("lib/python*/site-packages", "Lib/site-packages")
        for path in sorted((root / ".venv").glob(pattern))
    ]
    modules: dict[str, set[str]] = defaultdict(set)
    for distribution in importlib.metadata.distributions(path=paths) if paths else ():
        try:
            name = distribution.metadata.get("Name")
            names = (distribution.read_text("top_level.txt") or "").split() or [
                file.parts[0] if len(file.parts) > 1 else inspect.getmodulename(file.name) or ""
                for file in distribution.files or ()
            ]
        except (OSError, TypeError, UnicodeError, ValueError):
            continue
        if isinstance(name, str):
            modules[normalized_distribution(name)].update(
                module for module in names if module.isidentifier()
            )
    return {name: tuple(sorted(found)) for name, found in sorted(modules.items()) if found}


@dataclass(frozen=True, slots=True)
class ProductReferences:
    """Observed native identities and unreadable carriers, not call-time proof."""

    references: dict[str, set[str]]
    unknown_paths: tuple[str, ...] = ()
    # Identities that every consuming pipeline's own Forge runner declaration provides.
    runner_provided: dict[str, set[str]] = field(default_factory=dict)

    @property
    def coverage(self) -> Literal["evaluated", "unknown"]:
        """Describe native carrier coverage without claiming semantic correctness."""
        return "unknown" if self.unknown_paths else "evaluated"


def product_references_from_files(
    files: dict[str, str],
    *,
    context_files: dict[str, str] | None = None,
    declared_commands: Iterable[str] = (),
    include_declarations: bool = True,
    retained_steps: frozenset[tuple[str, str, str]] = frozenset(),
) -> ProductReferences:
    """Observe native references and keep malformed consumed carriers explicit."""
    declared_commands = tuple(declared_commands)
    command_sources = dict(context_files or {})
    command_sources.update(files)
    parsed_files = {
        path: python_references.complete_python_tree(text)
        for path, text in declaration_files(command_sources, "commands").items()
    }
    prefixes = python_references.cyclopts_prefixes(command_sources, parsed_files=parsed_files)
    command_owners = {
        path: python_references.cyclopts_command_owners(path, tree, prefixes)
        for path, tree in parsed_files.items()
        if tree is not None
    }
    known_commands = {
        normalize_command(command) for command in declared_commands if command.strip()
    }
    known_commands.update(command for commands in command_owners.values() for command in commands)
    command_vocabulary = command_references.CommandVocabulary.compile(known_commands)
    npm_scripts = npm_script_commands(command_sources)
    observed = {kind: set() for kind in REFERENCE_KINDS}
    if include_declarations:
        observed["command"].update(
            command
            for path in files
            if not path.startswith("tests/")
            for command in command_owners.get(path, {})
        )
    unknown_paths: list[str] = []
    for path, text in files.items():
        parsed = _file_references(
            path,
            text,
            command_vocabulary,
            npm_scripts,
            observed,
            include_declarations=include_declarations,
            parsed_files=parsed_files,
            retained_steps=retained_steps,
        )
        if not parsed:
            unknown_paths.append(path)
    observed["import"].difference_update(sys.stdlib_module_names)
    return ProductReferences(observed, tuple(sorted(unknown_paths)))


def reference_consumer_sources_from_files(
    files: dict[str, str],
    *,
    declared_commands: Iterable[str] = (),
    parsed_files: Mapping[str, AST | None] | None = None,
    retained_steps: frozenset[tuple[str, str, str]] = frozenset(),
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
            command_vocabulary,
            npm_scripts,
            observed,
            include_declarations=False,
            parsed_files=parsed_files,
            retained_steps=retained_steps,
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
    known_commands: command_references.CommandVocabulary,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    *,
    include_declarations: bool,
    parsed_files: Mapping[str, AST | None] | None = None,
    retained_steps: frozenset[tuple[str, str, str]] = frozenset(),
) -> bool:
    carrier = reference_carrier(path).name
    if carrier == "python":
        tree = (
            parsed_files.get(path)
            if parsed_files is not None
            else python_references.complete_python_tree(text)
        )
        if tree is None:
            return False
        imports, executables, inputs = python_references.python_references(tree, npm_scripts)
        observed["import"].update(imports)
        if not path.startswith("tests/"):
            observed["executable"].update(executables)
            observed["value"].update(inputs)
        return True
    if carrier == "pyproject":
        return pyproject_references(text, observed, declarations=include_declarations)
    if carrier == "package-json":
        return package_json_references(
            text, npm_scripts, observed, declarations=include_declarations
        )
    parsed = True
    if carrier == "yaml":
        # A step that the retention record binds by file, job and text is owned glue.
        retained = retained_step_texts(load_repository_paradigm(), path, text, retained_steps)
        parsed = _yaml_references(path, text, npm_scripts, observed, retained=retained)
    elif carrier == "shell":
        observed["executable"].update(
            command_references.shell_executables(
                text, npm_scripts, module_imports=observed["import"]
            )
        )
    elif carrier == "markdown":
        parsed = markdown_observation.markdown_references(
            path,
            text,
            known_commands,
            npm_scripts,
            observed,
            yaml_references=_yaml_references,
        )
    if (
        parsed
        and text.startswith("#!")
        and (executable := command_references.shebang_executable(text.splitlines()[0]))
    ):
        observed["executable"].add(executable)
    return parsed


def _yaml_references(
    path: str,
    text: str,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    *,
    retained: frozenset[str] = frozenset(),
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
                _configuration_reference(str(key), item, npm_scripts, observed, retained)
    return True


def _configuration_reference(
    key: str,
    item: object,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    retained: frozenset[str],
) -> None:
    if key == "uses" and isinstance(item, str):
        if reference := _github_reference(item):
            observed["reference"].add(reference)
    elif key in {"run", "script", "before_script", "after_script"}:
        commands = [item]
        while commands:
            command = commands.pop()
            if isinstance(command, list):
                commands.extend(command)
            elif isinstance(command, str) and command not in retained:
                # The Forge resolves an expression before the shell runs; it is a value.
                resolved = _FORGE_EXPRESSION.sub("$EXPRESSION", command)
                observed["executable"].update(
                    command_references.shell_executables(
                        resolved, npm_scripts, module_imports=observed["import"]
                    )
                )
    elif key == "image" and isinstance(item, str) and item:
        observed["reference"].add("docker")


_FORGE_EXPRESSION = re.compile(r"\$\{\{.*?\}\}", re.DOTALL)


def _github_reference(value: str) -> str:
    action = value.strip().strip("'\"")
    if not action or action.startswith("./"):
        return ""
    if action.startswith("docker://"):
        return "docker"
    return "github" if "@" in action and "/" in action.partition("@")[0] else ""


def deleted_input_gaps(
    files: Mapping[str, str], deleted: frozenset[str]
) -> tuple[list[str], list[str]]:
    """Close deleted paths against surviving explicit native command inputs.

    This bounded observation does not claim whole-program reference coverage.
    Unknown native input expressions stay distinct from known dangling inputs.
    """
    gaps, unknown = python_references.deleted_python_input_gaps(files, deleted)
    if not deleted:
        return gaps, unknown
    for path, text in files.items():
        if path.rsplit("/", 1)[-1] != "package.json":
            continue
        scripts = _native_scripts(text)
        if scripts is None:
            unknown.append(f"deleted_input_observation_unknown:{path}")
            continue
        for name, command in scripts.items():
            if not isinstance(command, str):
                unknown.append(f"deleted_input_observation_unknown:{path}:{name}")
                continue
            inputs, unresolved = command_references.shell_configuration_inputs(command)
            if unresolved:
                unknown.append(f"deleted_input_observation_unknown:{path}:{name}")
            for value in inputs:
                target = posixpath.normpath(posixpath.join(posixpath.dirname(path), value))
                if target in deleted:
                    gaps.append(f"deleted_input:{target}:{path}:scripts.{name}")
    return sorted(set(gaps)), sorted(set(unknown))


def _native_scripts(text: str) -> dict[str, object] | None:
    """Read the native scripts map without silently accepting malformed structure."""
    try:
        payload = json.loads(text)
    except ValueError:
        return None
    scripts = payload.get("scripts", {}) if isinstance(payload, dict) else None
    return scripts if isinstance(scripts, dict) else None
