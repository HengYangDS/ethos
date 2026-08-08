"""Observe typed product references across repository carriers."""

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
from ethos.repository.policy.references.carriers import REFERENCE_KINDS
from ethos.repository.policy.references.carriers import reference_carrier
from ethos.repository.policy.references.carriers import reference_paths
from ethos.repository.policy.references.commands import normalize_command

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def repository_product_references(root: Path) -> dict[str, set[str]]:
    """Observe typed machine references across active product surfaces."""
    return product_references_from_files(repository_reference_files(root), root=root)


def repository_reference_files(root: Path) -> dict[str, str]:
    """Read active carriers that may declare or consume product references."""
    files = {}
    for path in reference_paths(root, product_surface_files(root)):
        try:
            files[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
    return files


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
    npm_scripts = npm_script_commands(command_sources, root=root)
    observed = {kind: set() for kind in REFERENCE_KINDS}
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
    carrier = reference_carrier(path).name
    if carrier == "python":
        _python_file_references(path, text, prefixes, npm_scripts, observed)
        return
    if carrier == "pyproject":
        if include_declarations:
            pyproject_references(text, observed)
        return
    if carrier == "package-json":
        package_json_references(text, npm_scripts, observed, declarations=include_declarations)
        return
    if carrier == "yaml":
        _yaml_references(path, text, npm_scripts, observed)
    elif carrier == "shell":
        observed["executable"].update(command_references.shell_executables(text, npm_scripts))
    elif carrier == "markdown":
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


def npm_script_commands(files: dict[str, str], *, root: Path | None) -> dict[str, set[str]]:
    manifests: dict[str, str] = {}
    if root is not None:
        for path in product_surface_files(root):
            if path.name != "package.json":
                continue
            try:
                manifests[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
    manifests.update(
        {
            path: text
            for path, text in files.items()
            if reference_carrier(path).name == "package-json"
        }
    )
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


def reference_gaps(
    allowed: dict[str, frozenset[str]],
    observed: dict[str, set[str]],
) -> list[str]:
    gaps = []
    for kind in REFERENCE_KINDS:
        for reference in sorted(observed.get(kind, set()) - set(allowed.get(kind, ()))):
            if kind == "import" and reference in {"ethos", "tests", "tools"}:
                continue
            gaps.append(f"product_reference_not_admitted_at_baseline:{kind}:{reference}")
    return gaps


_MARKDOWN_FENCE = re.compile(
    r"^```(?P<language>[A-Za-z0-9_-]+)[^\n]*\n(?P<body>.*?)^```\s*$",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
_MARKDOWN_INLINE_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
