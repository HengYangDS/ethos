"""Positive product-reference ownership compiled from native declarations."""

from __future__ import annotations

import posixpath
import re
import tomllib
from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import StrictStr
from pydantic import ValidationError

import ethos.repository.policy.references.commands as command_references
import ethos.repository.policy.references.python_syntax as python_references
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import bind_gate_command
from ethos.repository.policy.references.carriers import REFERENCE_KINDS
from ethos.repository.policy.references.carriers import declaration_files
from ethos.repository.policy.references.carriers import reference_carrier
from ethos.repository.policy.references.manifests import PythonManifest
from ethos.repository.policy.references.manifests import normalized_distribution
from ethos.repository.policy.references.manifests import npm_script_commands
from ethos.repository.policy.references.manifests import package_json_references
from ethos.repository.policy.references.manifests import pyproject_references
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.release.resources import canonical_resource

if TYPE_CHECKING:
    from ast import AST
    from collections.abc import Mapping


def native_owned_references_from_files(
    files: dict[str, str],
    *,
    command_owners: dict[str, frozenset[str]] | None = None,
    distribution_modules: Mapping[str, tuple[str, ...]] | None = None,
) -> dict[str, frozenset[str]]:
    """Compile positive closure from native owners, resolving distributions as deptry does."""
    owned = {kind: set() for kind in REFERENCE_KINDS}
    npm_scripts = npm_script_commands(files)
    mappings, first_party = _python_import_owners(files)
    installed = distribution_modules or {}
    before = set(owned["distribution"])
    for text in declaration_files(files, "python-project").values():
        pyproject_references(text, owned)
    owned["import"].update(
        module
        for name in owned["distribution"] - before
        if not name.startswith("@")
        for module in mappings.get(name) or installed.get(name) or (name.replace("-", "_"),)
    )
    for text in declaration_files(files, "node-package").values():
        package_json_references(text, npm_scripts, owned, declarations=True)
    owned["import"].update(first_party)
    owned["command"].update(command_owners or command_owner_sources_from_files(files))
    _declared_gates(files, npm_scripts, owned)
    _declared_profiles(files, npm_scripts, owned)
    return {kind: frozenset(owned[kind]) for kind in REFERENCE_KINDS}


class _Runner(BaseModel):
    """What one Forge's CI runner environment provides to that Forge's own pipelines."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    forge: StrictStr
    executables: tuple[StrictStr, ...] = ()
    references: tuple[StrictStr, ...] = ()


def ci_runner_owners(files: dict[str, str]) -> dict[str, dict[str, frozenset[str]]]:
    """Return each Forge's declared runner identities; a malformed record declares nothing."""
    rows = _toml(_declaration_text(files, "ci-runners")).get("runner", [])
    try:
        runners = [_Runner.model_validate(row) for row in rows] if isinstance(rows, list) else []
    except ValidationError:
        return {}
    owners: dict[str, dict[str, set[str]]] = {}
    for runner in runners:
        provided = owners.setdefault(runner.forge, {"executable": set(), "reference": set()})
        provided["executable"].update(runner.executables)
        provided["reference"].update(runner.references)
    return {
        forge: {kind: frozenset(values) for kind, values in provided.items()}
        for forge, provided in owners.items()
    }


def command_owner_sources_from_files(
    files: dict[str, str],
    *,
    parsed_files: Mapping[str, AST | None] | None = None,
    context_files: dict[str, str] | None = None,
) -> dict[str, frozenset[str]]:
    """Return each command identity with every exact defining symbol."""
    sources = {
        path: text
        for path, text in declaration_files(files, "commands").items()
        if "App(" in text or ".command" in text
    }
    context = {
        path: text
        for path, text in declaration_files((context_files or {}) | files, "commands").items()
        if "App(" in text or ".command" in text
    }
    prefixes = python_references.cyclopts_prefixes(context, parsed_files=parsed_files)
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


def _python_import_owners(files: dict[str, str]) -> tuple[dict[str, tuple[str, ...]], set[str]]:
    payload = _toml(_declaration_text(files, "python-import-policy"))
    mappings: dict[str, tuple[str, ...]] = {}
    first_party = set(_string_items(payload.get("known_first_party")))
    native = payload.get("package_module_name_map")
    for distribution, modules in native.items() if isinstance(native, dict) else ():
        if names := ((modules,) if isinstance(modules, str) else _string_items(modules)):
            mappings[normalized_distribution(distribution)] = names
    for package in _table_items(payload.get("package")):
        first_party.update(_string_items(package.get("known_first_party")))
        for item in _string_items(package.get("package_module_name_map")):
            distribution, separator, modules = item.partition("=")
            if separator and distribution and (names := tuple(filter(None, modules.split("|")))):
                mappings[normalized_distribution(distribution)] = names
    return mappings, first_party


def _declared_gates(
    files: dict[str, str],
    npm_scripts: dict[str, set[str]],
    owned: dict[str, set[str]],
) -> None:
    try:
        if profiles := declaration_files(files, "profile"):
            profile = RepositoryProfileDeclaration.model_validate(
                _toml(next(iter(profiles.values())))
            )
            registry_path = profile.proof.gate_registry
            gates = (
                GateRegistryDeclaration.model_validate(_toml(files.get(registry_path, ""))).gates
                if registry_path
                else profile.proof.gates
            )
        else:
            gates = GateRegistryDeclaration.model_validate(
                _toml(_declaration_text(files, "gates"))
            ).gates
    except ValidationError:
        return
    commands = tuple(gate.command for gate in gates)
    selected_scripts: set[str] = set()
    for tokens in commands:
        command = bind_gate_command(tokens, "python")
        owned["executable"].update(
            command_references.command_executables(
                command, npm_scripts, module_imports=owned["import"]
            )
        )
        selected_scripts.update(
            token for token in command if token in files and token.endswith(".sh")
        )
    _declare_selected_scripts(files, selected_scripts, npm_scripts, owned)


def _declare_selected_scripts(
    files: dict[str, str],
    selected: set[str],
    npm_scripts: dict[str, set[str]],
    owned: dict[str, set[str]],
) -> None:
    pending = list(selected)
    visited: set[str] = set()
    while pending:
        path = pending.pop()
        if path in visited or (text := files.get(path)) is None:
            continue
        visited.add(path)
        owned["executable"].update(
            command_references.command_executables((path.rsplit("/", 1)[-1],), {})
        )
        owned["executable"].update(_invoked_executables(path, text, npm_scripts, owned["import"]))
        if text.startswith("#!") and (
            executable := command_references.shebang_executable(text.splitlines()[0])
        ):
            owned["executable"].add(executable)
        pending.extend(_selected_script_references(path, text, files) - visited)


def _invoked_executables(
    path: str, text: str, npm_scripts: dict[str, set[str]], imports: set[str]
) -> set[str]:
    """Compile one selected script with its own carrier syntax; other scripts stay shell."""
    try:
        carrier = reference_carrier(path).name
    except ValueError:
        carrier = "shell"
    if carrier == "python":
        tree = python_references.complete_python_tree(text)
        return python_references.python_references(tree, npm_scripts)[1] if tree else set()
    return command_references.shell_executables(text, npm_scripts, module_imports=imports)


def _selected_script_references(path: str, text: str, files: dict[str, str]) -> set[str]:
    parent = posixpath.dirname(path)
    references = set()
    for match in re.finditer(r"(?:\$\{?script_dir\}?/|\./)?[A-Za-z0-9_.-]+\.sh", text):
        token = match.group().removeprefix("./")
        if token.startswith(("${script_dir}/", "$script_dir/")):
            token = token.split("/", 1)[1]
        candidate = posixpath.normpath(posixpath.join(parent, token))
        if candidate in files:
            references.add(candidate)
    return references


def _declared_profiles(
    files: dict[str, str],
    npm_scripts: dict[str, set[str]],
    owned: dict[str, set[str]],
) -> None:
    _declared_profile_capabilities(files, owned)
    _declared_surface_references(files, owned)
    _declared_release_references(files, owned)
    _declared_tool_supply(files, owned)
    _declared_provider_references(files, npm_scripts, owned)


def _declared_profile_capabilities(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    try:
        profile = RepositoryProfileDeclaration.model_validate(
            _toml(_declaration_text(files, "profile"))
        )
    except ValidationError:
        return
    product = PythonManifest.read(canonical_resource("pyproject.toml").read_text(encoding="utf-8"))
    if product is not None:
        owned["executable"].update(product.project.scripts)
        owned["executable"].update(product.project.gui_scripts)
    # A governed repository may invoke what the product itself runs, as it may its scripts.
    surfaces = canonical_resource("system/surfaces.toml")
    if surfaces.is_file():
        product_surfaces = {"system/surfaces.toml": surfaces.read_text(encoding="utf-8")}
        _declared_surface_references(product_surfaces, owned)
    if profile.openspec is not None:
        owned["executable"].add("openspec")


def _declared_surface_references(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    surfaces = _toml(_declaration_text(files, "surfaces"))
    runtime = surfaces.get("runtime", {}) if isinstance(surfaces, dict) else {}
    if isinstance(runtime, dict):
        owned["value"].update(_string_items(runtime.get("inputs")))
        owned["executable"].update(_string_items(runtime.get("executables")))


def _declared_release_references(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    release = _toml(_declaration_text(files, "release"))
    host = release.get("host_profile", {}) if isinstance(release, dict) else {}
    if isinstance(host, dict) and isinstance(provider := host.get("provider"), str):
        owned["reference"].add(provider)
    publication = release.get("publication", {}) if isinstance(release, dict) else {}
    # Each publication peer names its forge and the Git remote that reaches it.
    for peer in _table_items(publication.get("peers") if isinstance(publication, dict) else None):
        names = {peer.get("provider"), peer.get("git_remote")}
        owned["reference"].update(name for name in names if isinstance(name, str))


def _declared_tool_supply(files: dict[str, str], owned: dict[str, set[str]]) -> None:
    for text in declaration_files(files, "tool-supply").values():
        supply = _toml(text)
        if isinstance(tool := supply.get("tool"), str):
            owned["executable"].add(tool)


def _declared_provider_references(
    files: dict[str, str],
    npm_scripts: dict[str, set[str]],
    owned: dict[str, set[str]],
) -> None:
    templates = _toml(_declaration_text(files, "providers"))
    selected_scripts: set[str] = set()
    for section in ("projection", "forge_surface"):
        for entry in _table_items(templates.get(section)):
            if isinstance(provider := entry.get("provider"), str):
                owned["reference"].add(provider)
            if isinstance(tool := entry.get("emulator_tool"), str):
                owned["executable"].add(tool)
            if entry.get("emulator_image"):
                owned["executable"].add("docker")
                owned["reference"].add("docker")
            selected_scripts.update(_string_items(entry.get("required_owner_scripts")))
            specific = entry.get("provider_specific_owner_scripts")
            if isinstance(specific, dict):
                selected_scripts.update(str(path) for path in specific)
    _declare_selected_scripts(files, selected_scripts, npm_scripts, owned)


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
