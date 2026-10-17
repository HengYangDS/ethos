"""Repository paradigm conformance over one repository's tracked paths.

Every obligation is decided from the tracked path set and the tracked carriers it
names. A gap carries its carrier, the violated obligation and the canonical repair.
"""

from __future__ import annotations

import json
import posixpath
import re
import tomllib
from typing import TYPE_CHECKING

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.contracts.verdict import close_verdict
from ethos.measure import effective_code_lines_for_source
from ethos.repository.paradigm.documents import document_gaps
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text
from ethos.repository.paradigm.names import authored_name_gaps
from ethos.repository.paradigm.names import name_path_gaps
from ethos.repository.paradigm.openspec import openspec_gaps
from ethos.repository.paradigm.pipelines import pipeline_model_gaps
from ethos.repository.paradigm.workspace import workspace_gaps
from ethos.repository.release.changelog import changelog_errors

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import EcosystemModule
    from ethos.contracts.paradigm.declaration import ReleaseConventions
    from ethos.contracts.paradigm.declaration import RepositoryParadigm

_KEBAB = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_NPM_DEPENDENCY_FIELDS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
)


def repository_paradigm_report(root: Path, *, tracked_paths: tuple[str, ...]) -> dict[str, object]:
    """Evaluate the shared repository paradigm over one repository's tracked paths."""
    paradigm = load_repository_paradigm()
    tracked = frozenset(tracked_paths)
    gaps = [
        *_root_gaps(paradigm, tracked),
        *_binding_gaps(paradigm, tracked),
        *_normalization_gaps(paradigm, root, tracked),
        *_configuration_gaps(paradigm, tracked),
        *_embedded_policy_gaps(paradigm, root, tracked),
        *_module_gaps(paradigm, root, tracked),
        *_size_gaps(paradigm, root, tracked),
        *_formatter_gaps(paradigm, root, tracked),
        *document_gaps(paradigm, root, tracked),
        *openspec_gaps(paradigm, root, tracked),
        *_peer_remote_gaps(paradigm, root, tracked),
        *workspace_gaps(paradigm, root, tracked),
        *_release_gaps(paradigm, root, tracked),
        *authored_name_gaps(paradigm, tracked),
        *pipeline_model_gaps(paradigm, tracked),
    ]
    required = [gap.required_gap for gap in gaps]
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(required)),
        "paradigm": paradigm.id,
        "gaps": [gap._asdict() for gap in gaps],
        "required_gaps": required,
        "next_action": gaps[0].repair if gaps else "",
    }


def paradigm_path_gaps(path: str) -> tuple[ParadigmGap, ...]:
    """Return the paradigm gaps that creating one tracked path would introduce.

    Every module's root entries are admitted here: whether a manifest applies is decided
    over the whole tree by the report.
    """
    paradigm = load_repository_paradigm()
    tracked = frozenset({path})
    return (
        *_root_entry_gaps(paradigm, tracked, _admitted_root_entries(paradigm, paradigm.module)),
        *_binding_gaps(paradigm, tracked),
        *_configuration_gaps(paradigm, tracked),
        *name_path_gaps(paradigm, path),
    )


def _admitted_root_entries(
    paradigm: RepositoryParadigm, modules: Iterable[EcosystemModule]
) -> frozenset[str]:
    """Return the catalogued root entries plus the given modules' manifest, lock and runners."""
    catalog = paradigm.root
    return frozenset(
        {
            *catalog.entry_documents,
            *catalog.protocol_files,
            *catalog.forge_entries,
            *catalog.governance_roots,
            *(
                name
                for module in modules
                for name in (module.manifest, module.lock, *module.runner_entries)
            ),
        }
    )


def _root_entry_gaps(
    paradigm: RepositoryParadigm, tracked: frozenset[str], admitted: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Admit only catalogued protocol entries at the root; non-dot directories are product-owned."""
    entries = {path.split("/", 1)[0]: "/" in path for path in tracked}
    for entry, directory in sorted(entries.items()):
        if entry in admitted or (directory and not entry.startswith(".")):
            continue
        carrier = paradigm.canonical_carrier(entry)
        repair = (
            f"move {entry} to {carrier} and pass it to its tool explicitly"
            if carrier
            else f"remove {entry} from the root or move it under a product directory"
        )
        yield ParadigmGap("root-catalog", entry, repair)


def _root_gaps(paradigm: RepositoryParadigm, tracked: frozenset[str]) -> Iterator[ParadigmGap]:
    """Report unadmitted root entries and missing required entry documents."""
    applied = [module for module in paradigm.module if module.manifest in tracked]
    yield from _root_entry_gaps(paradigm, tracked, _admitted_root_entries(paradigm, applied))
    for document in paradigm.root.required_documents:
        if document not in tracked:
            yield ParadigmGap("entry-documents", document, f"add {document} at the root")


def _binding_gaps(paradigm: RepositoryParadigm, tracked: frozenset[str]) -> Iterator[ParadigmGap]:
    """Admit only the ETHOS-defined binding files under the binding root."""
    prefix = f"{paradigm.binding.root}/"
    for path in sorted(tracked):
        if path.startswith(prefix) and path.removeprefix(prefix) not in paradigm.binding.files:
            yield ParadigmGap(
                "binding-files",
                path,
                f"move {path} into an ETHOS binding file or remove it",
            )


def _configuration_gaps(
    paradigm: RepositoryParadigm, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Admit only consumed configuration, grouped by consuming tool or repository check."""
    plane = paradigm.configuration
    prefix = f"{plane.root}/"
    owners = paradigm.owner_directories()
    for path in sorted(entry for entry in tracked if entry.startswith(prefix)):
        parts = path.removeprefix(prefix).split("/")
        if path.endswith(".md"):
            yield ParadigmGap(
                "configuration-carrier", path, f"move {path} out of {prefix} into the documentation"
            )
        elif parts[0] in plane.planes or "/".join(parts) in plane.files:
            continue
        elif parts[0] not in plane.owner_groups or len(parts) < 3:
            groups = "|".join(plane.owner_groups)
            yield ParadigmGap(
                "configuration-group",
                path,
                f"move {path} under {prefix}<{groups}>/<owner>/ or a toolchain root",
            )
        elif not _KEBAB.fullmatch(parts[1]):
            yield ParadigmGap(
                "configuration-owner", path, f"name {prefix}{parts[0]}/{parts[1]} in kebab-case"
            )
        else:
            yield from _owner_file_gaps(paradigm, owners, path, parts)


def _owner_file_gaps(
    paradigm: RepositoryParadigm,
    owners: dict[str, tuple[frozenset[str], bool]],
    path: str,
    parts: list[str],
) -> Iterator[ParadigmGap]:
    """Keep a tool's native names in its own directory and repository parameters in policy."""
    directory = posixpath.join(paradigm.configuration.root, parts[0], parts[1])
    admitted, nested = owners.get(directory, (frozenset(), False))
    basename = parts[-1]
    if len(parts) == 3 and basename in admitted | {paradigm.configuration.policy}:
        return
    if nested and len(parts) > 3:
        return
    carrier = paradigm.native_carrier(basename)
    if carrier and carrier != path:
        yield ParadigmGap("configuration-owner", path, f"move {path} to {carrier}")
    else:
        yield ParadigmGap(
            "configuration-carrier",
            path,
            f"keep only native {parts[1]} configuration or {directory}/"
            f"{paradigm.configuration.policy} in {directory}/",
        )


def _embedded_policy_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Keep tool policy that a tool reads from an explicit file out of package manifests."""
    project = tracked_text(root, "pyproject.toml", tracked)
    try:
        tables = tomllib.loads(project).get("tool", {}) if project is not None else {}
    except tomllib.TOMLDecodeError:
        tables = {}
    package = tracked_text(root, "package.json", tracked)
    try:
        keys = json.loads(package) if package is not None else {}
    except json.JSONDecodeError:
        keys = {}
    for tool in paradigm.tool:
        for table in tool.manifest_tables:
            if isinstance(tables, dict) and table in tables:
                yield ParadigmGap(
                    "embedded-policy",
                    f"pyproject.toml:tool.{table}",
                    f"move [tool.{table}] to {tool.carrier} and pass it explicitly",
                )
        for key in tool.package_keys:
            if isinstance(keys, dict) and key in keys:
                yield ParadigmGap(
                    "embedded-policy",
                    f"package.json:{key}",
                    f"move the package.json {key} key to {tool.carrier} and pass it explicitly",
                )


def _normalization_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Require UTF-8, LF line endings and a final newline in both declaration carriers."""
    rule = paradigm.normalization.gitattributes
    attributes = tracked_text(root, ".gitattributes", tracked)
    declared = [" ".join(line.split()) for line in (attributes or "").splitlines()]
    catch_all = [line for line in declared if line.split(" ", 1)[0] == "*"]
    if not catch_all or catch_all[-1] != rule:
        yield ParadigmGap(
            "text-normalization",
            ".gitattributes",
            f"declare `{rule}` as the last pattern for every file in .gitattributes",
        )
    expected = paradigm.normalization.editorconfig.model_dump()
    editor = tracked_text(root, ".editorconfig", tracked)
    defaults = editor_defaults(editor) if editor is not None else {}
    if any(defaults.get(key) != value for key, value in expected.items()):
        settings = ", ".join(f"{key} = {value}" for key, value in expected.items())
        yield ParadigmGap(
            "text-normalization", ".editorconfig", f"declare {settings} under [*] in .editorconfig"
        )


def _module_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Lock every applied ecosystem module and keep the declared language floor."""
    for module in paradigm.module:
        if module.manifest not in tracked:
            continue
        source = tracked_text(root, module.manifest, tracked)
        if source is None:
            yield ParadigmGap(
                "module-lock", module.manifest, f"restore a readable {module.manifest}"
            )
            continue
        if module.lock not in tracked and _requires_lock(module, source):
            yield ParadigmGap(
                "module-lock", module.manifest, f"lock {module.manifest} with {module.lock}"
            )
        if module.floor and _python_floor(source) != module.floor:
            yield ParadigmGap(
                "module-floor",
                module.manifest,
                f"declare requires-python with the lower bound >={module.floor}",
            )


def python_size_gaps(root: Path, tracked_paths: Iterable[str]) -> tuple[ParadigmGap, ...]:
    """Measure every tracked Python file against the shared effective-line ceiling."""
    ceiling = load_repository_paradigm().size.python_effective_lines
    gaps: list[ParadigmGap] = []
    for path in sorted(entry for entry in set(tracked_paths) if entry.endswith(".py")):
        carrier = root / path
        if not carrier.is_file():
            continue
        try:
            effective = effective_code_lines_for_source(carrier.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, SyntaxError, ValueError):
            repair = f"make {path} readable UTF-8 Python so it can be measured"
            gaps.append(ParadigmGap("python-size", path, repair))
            continue
        if effective > ceiling:
            repair = f"split {path} by semantic ownership to at most {ceiling} effective lines"
            gaps.append(ParadigmGap("python-size", path, repair))
    return tuple(gaps)


def _formatter_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Bind each tracked authored carrier class to its common formatter and settings."""
    carriers = {tool.id: tool.carrier for tool in paradigm.tool}
    authored = [path for path in tracked if not path.startswith(paradigm.immutable_roots)]
    for formatter in paradigm.formatter:
        if not any(path.endswith(formatter.suffixes) for path in authored):
            continue
        carrier = carriers[formatter.tool]
        source = tracked_text(root, carrier, tracked)
        if source is None:
            classes = "/".join(formatter.suffixes)
            yield ParadigmGap(
                "formatter-binding",
                carrier,
                f"bind {formatter.tool} at {carrier} for the tracked {classes} carriers",
            )
            continue
        try:
            declared = tomllib.loads(source)
        except tomllib.TOMLDecodeError:
            declared = {}
        for key, expected in formatter.settings.items():
            if _declared_setting(declared, key) != expected:
                yield ParadigmGap(
                    "formatter-setting",
                    f"{carrier}:{key}",
                    f"set {key} to {expected!r} in {carrier}",
                )


def _peer_remote_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Name each publication peer's Git remote after the peer itself."""
    release = f"{paradigm.binding.root}/release.toml"
    source = tracked_text(root, release, tracked)
    try:
        declared = tomllib.loads(source) if source is not None else {}
    except tomllib.TOMLDecodeError:
        return  # The release policy report owns an unreadable release binding.
    publication = declared.get("publication", {})
    peers = publication.get("peers", []) if isinstance(publication, dict) else []
    for peer in peers if isinstance(peers, list) else ():
        if not isinstance(peer, dict) or not isinstance(peer.get("id"), str):
            continue
        identity, remote = peer["id"], peer.get("git_remote")
        if remote != identity:
            yield ParadigmGap(
                "peer-remote",
                f"{release}:publication.peers.{identity}",
                f'set git_remote = "{identity}" and run git remote rename {remote} {identity}',
            )


def _release_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Keep one version source and one changelog grammar in a repository that tags releases."""
    release = f"{paradigm.binding.root}/release.toml"
    source = tracked_text(root, release, tracked)
    try:
        declared = tomllib.loads(source) if source is not None else {}
    except tomllib.TOMLDecodeError:
        return  # The release policy report owns an unreadable release binding.
    protected = declared.get("protected_refs", {})
    tags = protected.get("tags") if isinstance(protected, dict) else None
    if not tags:
        return
    conventions = paradigm.release
    if tags != [conventions.tag_pattern]:
        yield ParadigmGap(
            "release-tags",
            f"{release}:protected_refs.tags",
            f'tag releases as ["{conventions.tag_pattern}"] followed by a SemVer version',
        )
    if conventions.version_file not in tracked:
        yield ParadigmGap(
            "version-source",
            conventions.version_file,
            f"add {conventions.version_file} as the only version source",
        )
    project = tracked_text(root, "pyproject.toml", tracked)
    try:
        section = tomllib.loads(project).get("project", {}) if project is not None else {}
    except tomllib.TOMLDecodeError:
        section = {}
    if isinstance(section, dict) and "version" in section:
        yield ParadigmGap(
            "version-source",
            "pyproject.toml:project.version",
            f"declare the version dynamic and read it from {conventions.version_file}",
        )
    package = tracked_text(root, "package.json", tracked)
    try:
        manifest = json.loads(package) if package is not None else {}
    except json.JSONDecodeError:
        manifest = {}
    if isinstance(manifest, dict) and "version" in manifest:
        yield ParadigmGap(
            "version-source",
            "package.json:version",
            f"remove the literal version; {conventions.version_file} is the only version source",
        )
    yield from _changelog_gaps(conventions, tracked_text(root, conventions.changelog, tracked))


def _changelog_gaps(conventions: ReleaseConventions, text: str | None) -> Iterator[ParadigmGap]:
    """Project the common parsed release-note contract as a repository gap."""
    if text is None:
        yield ParadigmGap(
            "changelog", conventions.changelog, f"add {conventions.changelog} (Keep a Changelog)"
        )
        return
    if errors := changelog_errors(text):
        yield ParadigmGap(
            "changelog",
            conventions.changelog,
            f"correct {conventions.changelog}: {', '.join(errors)}",
        )


def _declared_setting(declared: object, key: str) -> object:
    """Read one dotted formatter setting from its native declaration."""
    for part in key.split("."):
        declared = declared.get(part) if isinstance(declared, dict) else None
    return declared


def _size_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Hold every tracked Python file to the shared ceiling, which no binding restates."""
    yield from python_size_gaps(root, tracked)
    rules = tracked_text(root, f"{paradigm.binding.root}/rules.toml", tracked)
    try:
        quality = tomllib.loads(rules).get("quality", {}) if rules is not None else {}
    except tomllib.TOMLDecodeError:
        quality = {}
    if isinstance(quality, dict) and "code_size" in quality:
        yield ParadigmGap(
            "binding-restatement",
            f"{paradigm.binding.root}/rules.toml:quality.code_size",
            "remove [quality.code_size]; the repository paradigm owns the size ceilings",
        )


def _requires_lock(module: EcosystemModule, source: str) -> bool:
    """Return whether the manifest declares what its lock must resolve."""
    if module.lock_scope == "manifest":
        return True
    if module.id == "go":
        return any(line.strip().startswith("require") for line in source.splitlines())
    try:
        manifest = json.loads(source)
    except json.JSONDecodeError:
        return True
    return not isinstance(manifest, dict) or any(
        manifest.get(field) for field in _NPM_DEPENDENCY_FIELDS
    )


def _python_floor(source: str) -> str:
    """Return the single lower bound of the declared requires-python specifier."""
    try:
        project = tomllib.loads(source).get("project", {})
    except tomllib.TOMLDecodeError:
        return ""
    specifier = project.get("requires-python") if isinstance(project, dict) else None
    if not isinstance(specifier, str):
        return ""
    bounds = [
        part.strip()[2:].strip() for part in specifier.split(",") if part.strip().startswith(">=")
    ]
    return bounds[0] if len(bounds) == 1 else ""


def editor_defaults(source: str) -> dict[str, str]:
    """Return the lowercased properties of the EditorConfig section that matches every file."""
    section = ""
    values: dict[str, str] = {}
    for raw in source.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
        elif section == "*" and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip().lower()] = value.strip().lower()
    return values
