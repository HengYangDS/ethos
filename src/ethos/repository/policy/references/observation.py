"""Observe typed product references across repository carriers."""

from __future__ import annotations

import posixpath
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Literal

import ethos.repository.policy.references.commands.invocation as command_references
import ethos.repository.policy.references.commands.vocabulary as command_declarations
import ethos.repository.policy.references.markdown as markdown_observation
import ethos.repository.policy.references.python.syntax as python_references
from ethos.repository.policy.boundary.product import product_surface_files
from ethos.repository.policy.references.carriers import REFERENCE_KINDS
from ethos.repository.policy.references.carriers import reference_carrier
from ethos.repository.policy.references.carriers import reference_paths
from ethos.repository.policy.references.commands.vocabulary import normalize_command
from ethos.repository.policy.references.configuration import yaml_references
from ethos.repository.policy.references.manifests import NodeManifest
from ethos.repository.policy.references.manifests import npm_script_commands
from ethos.repository.policy.references.manifests import package_json_references
from ethos.repository.policy.references.manifests import pyproject_references
from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns

if TYPE_CHECKING:
    from ast import AST
    from collections.abc import Iterable
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.repository.policy.references.python.bindings import ReferenceUncertainty


@dataclass(frozen=True, slots=True)
class RepositoryReferenceObservation:
    """One finite read of current reference carriers and unreadable paths."""

    files: dict[str, str]
    unreadable_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReferenceConsumption:
    """Current consumer relation, carrier failures and bounded semantic residuals."""

    sources: dict[str, dict[str, frozenset[str]]]
    unknown_paths: tuple[str, ...]
    uncertainties: tuple[ReferenceUncertainty, ...] = ()


@dataclass(frozen=True, slots=True)
class ProductReferences:
    """Observed identities never discard unsupported carrier or consumer semantics."""

    references: dict[str, set[str]]
    unknown_paths: tuple[str, ...] = ()
    uncertainties: tuple[ReferenceUncertainty, ...] = ()

    @property
    def coverage(self) -> Literal["evaluated", "partial", "unknown"]:
        """Never equate successful parsing with closed reference semantics."""
        if self.unknown_paths or any(item.state == "unknown" for item in self.uncertainties):
            return "unknown"
        return "partial" if self.uncertainties else "evaluated"


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
) -> ProductReferences:
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
    command_vocabulary = command_declarations.CommandVocabulary.compile(known_commands)
    npm_scripts = npm_script_commands(command_sources)
    source_trees = {
        path: python_references.complete_python_tree(text)
        for path, text in command_sources.items()
        if reference_carrier(path).name == "python"
    }
    observed = {kind: set() for kind in REFERENCE_KINDS}
    uncertainties: list[ReferenceUncertainty] = []
    unknown_paths: list[str] = []
    for path, text in files.items():
        sources = (
            PythonSourceReturns(command_sources, source_trees, PythonReferenceFlow)
            if reference_carrier(path).name == "python"
            else None
        )
        parsed = _file_references(
            path,
            text,
            prefixes,
            command_vocabulary,
            npm_scripts,
            observed,
            include_declarations=include_declarations,
            require_complete=True,
            parsed_files=source_trees,
            uncertainties=uncertainties,
            sources=sources,
        )
        if not parsed:
            unknown_paths.append(path)
    observed["import"].difference_update(sys.stdlib_module_names)
    return ProductReferences(observed, tuple(sorted(unknown_paths)), tuple(uncertainties))


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
    command_vocabulary = command_declarations.CommandVocabulary.compile(known_commands)
    npm_scripts = npm_script_commands(files)
    source_trees = (
        parsed_files
        if parsed_files is not None
        else {
            path: python_references.complete_python_tree(text)
            for path, text in files.items()
            if reference_carrier(path).name == "python"
        }
    )
    consumers = {kind: defaultdict(set) for kind in REFERENCE_KINDS}
    unknown_paths: list[str] = []
    uncertainties: list[ReferenceUncertainty] = []
    for path, text in files.items():
        sources = (
            PythonSourceReturns(files, source_trees, PythonReferenceFlow)
            if reference_carrier(path).name == "python"
            else None
        )
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
            parsed_files=source_trees,
            uncertainties=uncertainties,
            sources=sources,
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
        uncertainties=tuple(uncertainties),
    )


def _file_references(
    path: str,
    text: str,
    prefixes: dict[tuple[str, str], str],
    known_commands: command_declarations.CommandVocabulary,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    *,
    include_declarations: bool,
    require_complete: bool = False,
    parsed_files: Mapping[str, AST | None] | None = None,
    uncertainties: list[ReferenceUncertainty] | None = None,
    sources: PythonSourceReturns | None = None,
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
            uncertainties=uncertainties,
            sources=sources,
        )
    if carrier == "pyproject":
        return pyproject_references(text, observed, declarations=include_declarations)
    if carrier == "package-json":
        return package_json_references(
            text, npm_scripts, observed, declarations=include_declarations
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
    uncertainties: list[ReferenceUncertainty] | None,
    sources: PythonSourceReturns | None,
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
    return _python_file_references(
        path,
        text,
        prefixes,
        npm_scripts,
        observed,
        include_declarations=include_declarations,
        trees=(tree,) if tree is not None else None,
        uncertainties=uncertainties,
        sources=sources,
    )


def _text_carrier_references(
    *,
    carrier: str,
    path: str,
    text: str,
    known_commands: command_declarations.CommandVocabulary,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
) -> bool:
    if carrier == "yaml":
        return yaml_references(path, text, npm_scripts, observed)
    if carrier == "shell":
        observed["executable"].update(
            command_references.shell_executables(
                text, npm_scripts, module_imports=observed["import"]
            )
        )
    elif carrier == "markdown":
        return markdown_observation.markdown_references(
            path,
            text,
            known_commands,
            npm_scripts,
            observed,
            yaml_references=yaml_references,
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
    uncertainties: list[ReferenceUncertainty] | None = None,
    sources: PythonSourceReturns | None = None,
) -> bool:
    for tree in trees or python_references.python_trees(text):
        try:
            consumption = PythonReferenceFlow(path, npm_scripts, sources=sources).observe(
                tree, source=text
            )
        except (SyntaxError, ValueError):
            return False
        observed["import"].update(consumption.imports)
        if uncertainties is not None:
            uncertainties.extend(
                item
                for item in consumption.uncertainties
                if not path.startswith("tests/") or item.kind == "import"
            )
        if path.startswith("tests/"):
            continue
        observed["executable"].update(consumption.executables)
        observed["value"].update(consumption.inputs)
        if include_declarations:
            observed["command"].update(
                python_references.cyclopts_command_owners(path, tree, prefixes)
            )
    return True


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
    manifest = NodeManifest.read(text)
    return dict(manifest.scripts) if manifest is not None else None
