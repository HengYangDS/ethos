"""Repository paradigm conformance over one repository's tracked paths.

Every obligation is decided from the tracked path set and the tracked carriers it
names. A gap carries its carrier, the violated obligation and the canonical repair.
"""

from __future__ import annotations

import json
import tomllib
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.contracts.verdict import close_verdict

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import EcosystemModule
    from ethos.contracts.paradigm.declaration import RepositoryParadigm

_NPM_DEPENDENCY_FIELDS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
)


class ParadigmGap(NamedTuple):
    """One paradigm gap with its carrier, violated obligation and canonical repair."""

    obligation: str
    carrier: str
    repair: str

    @property
    def required_gap(self) -> str:
        """Return the stable gap identity that proof, land and publish report."""
        return f"repository_paradigm_{self.obligation.replace('-', '_')}:{self.carrier}"


def repository_paradigm_report(root: Path, *, tracked_paths: tuple[str, ...]) -> dict[str, object]:
    """Evaluate the shared repository paradigm over one repository's tracked paths."""
    paradigm = load_repository_paradigm()
    tracked = frozenset(tracked_paths)
    gaps = [
        *_root_gaps(paradigm, tracked),
        *_binding_gaps(paradigm, tracked),
        *_normalization_gaps(paradigm, root, tracked),
        *_embedded_policy_gaps(paradigm, root, tracked),
        *_module_gaps(paradigm, root, tracked),
    ]
    required = [gap.required_gap for gap in gaps]
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(required)),
        "paradigm": paradigm.id,
        "gaps": [gap._asdict() for gap in gaps],
        "required_gaps": required,
        "next_action": gaps[0].repair if gaps else "",
    }


def _root_gaps(paradigm: RepositoryParadigm, tracked: frozenset[str]) -> Iterator[ParadigmGap]:
    """Admit only catalogued protocol entries at the root; non-dot directories are product-owned."""
    catalog = paradigm.root
    applied = [module for module in paradigm.module if module.manifest in tracked]
    admitted = {
        *catalog.entry_documents,
        *catalog.protocol_files,
        *catalog.forge_entries,
        *catalog.governance_roots,
        *(name for module in applied for name in (module.manifest, module.lock)),
        *(name for module in applied for name in module.runner_entries),
    }
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
    for document in catalog.required_documents:
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


def _embedded_policy_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Keep tool policy that a tool reads from an explicit file out of package manifests."""
    project = _tracked_text(root, "pyproject.toml", tracked)
    try:
        tables = tomllib.loads(project).get("tool", {}) if project is not None else {}
    except tomllib.TOMLDecodeError:
        tables = {}
    package = _tracked_text(root, "package.json", tracked)
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
    attributes = _tracked_text(root, ".gitattributes", tracked)
    declared = [" ".join(line.split()) for line in (attributes or "").splitlines()]
    catch_all = [line for line in declared if line.split(" ", 1)[0] == "*"]
    if not catch_all or catch_all[-1] != rule:
        yield ParadigmGap(
            "text-normalization",
            ".gitattributes",
            f"declare `{rule}` as the last pattern for every file in .gitattributes",
        )
    expected = paradigm.normalization.editorconfig.model_dump()
    editor = _tracked_text(root, ".editorconfig", tracked)
    defaults = _editor_defaults(editor) if editor is not None else {}
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
        source = _tracked_text(root, module.manifest, tracked)
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


def _editor_defaults(source: str) -> dict[str, str]:
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


def _tracked_text(root: Path, path: str, tracked: frozenset[str]) -> str | None:
    """Read one tracked carrier as UTF-8 text, or return None when it is absent or unreadable."""
    if path not in tracked:
        return None
    try:
        return (root / path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
