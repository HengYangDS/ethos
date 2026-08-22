"""Positive product-reference ownership compiled from native declarations."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import ethos.repository.policy.references.commands as command_references
import ethos.repository.policy.references.python_syntax as python_references
from ethos.repository.policy.references.carriers import REFERENCE_KINDS
from ethos.repository.policy.references.carriers import declaration_files
from ethos.repository.policy.references.observation import normalized_distribution
from ethos.repository.policy.references.observation import npm_script_commands
from ethos.repository.policy.references.observation import package_json_references
from ethos.repository.policy.references.observation import pyproject_references

if TYPE_CHECKING:
    from ast import AST
    from collections.abc import Mapping


def native_owned_references_from_files(
    files: dict[str, str],
    *,
    command_owners: dict[str, frozenset[str]] | None = None,
) -> dict[str, frozenset[str]]:
    """Compile the positive closure from package, command, tool, and profile owners."""
    owned = {kind: set() for kind in REFERENCE_KINDS}
    npm_scripts = npm_script_commands(files)
    mappings, first_party = _python_import_owners(files)
    before = set(owned["distribution"])
    for text in declaration_files(files, "python-project").values():
        pyproject_references(text, owned)
    owned["import"].update(
        mappings.get(name, name.replace("-", "_"))
        for name in owned["distribution"] - before
        if not name.startswith("@")
    )
    for text in declaration_files(files, "node-package").values():
        package_json_references(text, npm_scripts, owned, declarations=True)
    owned["import"].update(first_party)
    owned["command"].update(command_owners or command_owner_sources_from_files(files))
    _declared_gates(files, npm_scripts, owned)
    _declared_tools(files, owned)
    _declared_profiles(files, owned)
    return {kind: frozenset(owned[kind]) for kind in REFERENCE_KINDS}


def command_owner_sources_from_files(
    files: dict[str, str],
    *,
    parsed_files: Mapping[str, AST | None] | None = None,
) -> dict[str, frozenset[str]]:
    """Return each command identity with every exact defining symbol."""
    sources = {
        path: text
        for path, text in declaration_files(files, "commands").items()
        if "App(" in text or ".command" in text
    }
    prefixes = python_references.cyclopts_prefixes(sources, parsed_files=parsed_files)
    owners: dict[str, set[str]] = {}
    module_paths = {python_references.module_name(path): path for path in sources}
    for (module, variable), command in prefixes.items():
        if command and (path := module_paths.get(module)):
            owners.setdefault(command, set()).add(f"{path}:{variable}")
    for path, text in sources.items():
        tree = parsed_files.get(path) if parsed_files is not None else None
        trees = (
            (tree,)
            if tree is not None
            else (() if parsed_files is not None else python_references.python_trees(text))
        )
        for tree in trees:
            for command, symbols in python_references.cyclopts_command_owners(
                path, tree, prefixes
            ).items():
                owners.setdefault(command, set()).update(symbols)
    return {command: frozenset(symbols) for command, symbols in owners.items()}


def _python_import_owners(files: dict[str, str]) -> tuple[dict[str, str], set[str]]:
    payload = _toml(_declaration_text(files, "python-import-policy"))
    mappings: dict[str, str] = {}
    first_party = set()
    for package in _table_items(payload.get("package")):
        first_party.update(_string_items(package.get("known_first_party")))
        for item in _string_items(package.get("package_module_name_map")):
            distribution, separator, module = item.partition("=")
            if separator and distribution and module:
                mappings[normalized_distribution(distribution)] = module
    return mappings, first_party


def _declared_gates(
    files: dict[str, str],
    npm_scripts: dict[str, set[str]],
    owned: dict[str, set[str]],
) -> None:
    payload = _toml(_declaration_text(files, "gates"))
    for gate in _table_items(payload.get("gates")):
        command = tuple(_string_items(gate.get("command")))
        owned["executable"].update(command_references.command_executables(command, npm_scripts))


def _declared_tools(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    payload = _toml(_declaration_text(files, "tools"))
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
    profile = _toml(_declaration_text(files, "profile"))
    if isinstance(profile.get("openspec"), dict):
        owned["executable"].add("openspec")


def _declared_surface_inputs(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    surfaces = _toml(_declaration_text(files, "surfaces"))
    runtime = surfaces.get("runtime", {}) if isinstance(surfaces, dict) else {}
    if isinstance(runtime, dict):
        owned["value"].update(_string_items(runtime.get("inputs")))


def _declared_release_references(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    release = _toml(_declaration_text(files, "release"))
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
    templates = _toml(_declaration_text(files, "providers"))
    for section in ("projection", "forge_surface"):
        for entry in _table_items(templates.get(section)):
            if isinstance(provider := entry.get("provider"), str):
                owned["reference"].add(provider)
            if isinstance(tool := entry.get("emulator_tool"), str):
                owned["executable"].add(tool)
            if entry.get("emulator_image"):
                owned["executable"].add("docker")
                owned["reference"].add("docker")


def _declaration_text(files: dict[str, str], declaration: str) -> str:
    return "\n".join(declaration_files(files, declaration).values())


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
    return tuple(
        {str(key): entry for key, entry in item.items()} for item in value if isinstance(item, dict)
    )
