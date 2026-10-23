"""Prepare exact native formatter postimages without writing repository source."""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ruff import find_ruff_bin

from ethos.adapters.gates.native.inputs import authored_source_files
from ethos.adapters.gates.native.inputs import authored_text_files
from ethos.adapters.gates.native.inputs import authored_text_gaps
from ethos.adapters.gates.native.inputs import format_ownership
from ethos.adapters.gates.native.inputs import native_configurations
from ethos.adapters.gates.native.inputs import native_repository_configuration
from ethos.adapters.gates.native.inputs import quality_inventory_failure
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.runtime.filesystem import runtime_scripts
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.repository.release.resources import canonical_resource

_SUFFIXES = frozenset(
    {
        ".py",
        ".pyi",
        ".md",
        ".toml",
        ".yaml",
        ".yml",
        ".json",
        ".js",
        ".mjs",
        ".cjs",
        ".sh",
        ".bash",
        ".svg",
    }
)
_NODE_FORMATTERS = frozenset({"prettier", "taplo", "svgo"})
# A named path that a formatter could read as a pattern is rendered alone.
_PATTERN_CHARACTERS = frozenset("*?[]{}")
_PRETTIER_SKIPPED_DIRECTORIES = frozenset({".git", ".hg", ".jj", ".sl", ".svn", "node_modules"})
# Paths per native check run stay far below the Windows command-line limit.
_CHECK_ARGUMENT_BUDGET = 6000
_TAPLO_COLLECTED = re.compile(rb"found files total=(\d+) excluded=(\d+)")
_ANSI_ESCAPE = re.compile(rb"\x1b\[[0-9;]*m")


@dataclass(frozen=True)
class FormattedFile:
    """One literal path, original content and native postimage with preserved mode."""

    path: str
    before: bytes
    after: bytes
    mode: int
    ignored: bool = False


def _selected_files(
    root: Path, requested: tuple[str, ...], authored: list[str]
) -> tuple[tuple[str, str], ...]:
    selected_paths = set(authored)
    files = [
        relative
        for relative in requested or authored
        if _candidate_path(
            root, relative, excluded=relative not in selected_paths, explicit=bool(requested)
        )
    ]
    ownership = format_ownership(root, tuple(dict.fromkeys(files)))
    if ownership["verdict"] != "pass":
        raise ValueError(str(ownership["failures"]))
    selected = []
    for item in ownership["assignments"]:
        if item["mutation_policy"] != "native-formatter":
            if requested:
                message = f"source_format_other_owner:{item['path']}"
                raise ValueError(message)
            continue
        selected.append((item["path"], item["format_owner"]))
    return tuple(selected)


def _candidate_path(root: Path, relative: str, *, excluded: bool, explicit: bool) -> bool:
    raw, path = Path(relative), root / relative
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        message = f"source_format_path_invalid:{relative}"
        raise ValueError(message)
    if excluded or raw.suffix.lower() not in _SUFFIXES:
        if explicit:
            message = f"source_format_other_owner:{relative}"
            raise ValueError(message)
        return False
    if not path.is_file() and explicit:
        message = f"source_format_input_missing:{relative}"
        raise FileNotFoundError(message)
    return path.is_file()


def _run(
    root: Path,
    command: tuple[str, ...],
    content: bytes | None = None,
    *,
    reject_diagnostics: bool = False,
) -> bytes:
    completed = run_command(
        root,
        command,
        stdin=content,
        text=False,
        timeout=30,
        env={"NODE_DISABLE_COMPILE_CACHE": "1"},
        remove_env=("NODE_COMPILE_CACHE", "NODE_OPTIONS", "NODE_PATH", "TAPLO_CONFIG"),
    )
    if completed.returncode or (reject_diagnostics and completed.stderr):
        raise subprocess.CalledProcessError(
            completed.returncode, command, completed.stdout, completed.stderr
        )
    return completed.stdout


def _prettier(
    root: Path, relative: str, content: bytes, *, repository_policy: bool, node: str | None
) -> tuple[bytes, bool]:
    binary = (
        node or str(resolve_node_runtime().executable),
        str(product_node_module("prettier") / "bin/prettier.cjs"),
    )
    ignore = native_repository_configuration(root, "prettier-ignore") if repository_policy else None
    ignored = (
        repository_policy
        and json.loads(
            _run(
                root,
                (
                    *binary,
                    "--ignore-path",
                    str(ignore) if ignore is not None else os.devnull,
                    "--file-info",
                    str(root / relative),
                ),
            )
        )["ignored"]
    )
    if ignored:
        return content, True
    configurations = (
        native_configurations(root, "prettier", ".config/checks/prettier/prettier.toml")
        if repository_policy
        else (str(canonical_resource(".config/checks/prettier/prettier.toml")),)
    )
    rendered = [
        _run(
            root,
            (
                *binary,
                "--config",
                config,
                "--no-editorconfig",
                "--prose-wrap",
                "preserve",
                "--ignore-path",
                os.devnull,
                "--stdin-filepath",
                relative,
            ),
            content,
            reject_diagnostics=True,
        )
        for config in configurations
    ]
    if any(value != rendered[0] for value in rendered[1:]):
        message = f"native_formatter_policy_conflict:{relative}"
        raise ValueError(message)
    return rendered[0], False


def render_source_content(
    root: Path,
    relative: str,
    owner: str,
    content: bytes,
    *,
    repository_policy: bool = True,
    node: str | None = None,
) -> tuple[bytes, bool]:
    """Render one original native postimage for authored checks or owned projections.

    Callers that render many files pass ``node``, one resolved Node executable.
    """
    if owner == "prettier":
        return _prettier(root, relative, content, repository_policy=repository_policy, node=node)
    scripts = runtime_scripts(Path(sys.prefix))
    if owner == "ruff":
        rendered = tuple(
            _run(
                root,
                (
                    str(find_ruff_bin()),
                    "format",
                    "--no-cache",
                    "--no-respect-gitignore",
                    "--config",
                    config,
                    "--stdin-filename",
                    relative,
                    "-",
                ),
                content,
            )
            for config in native_configurations(root, "ruff", ".config/checks/ruff/ruff.toml")
        )
        if any(value != rendered[0] for value in rendered[1:]):
            message = f"native_formatter_policy_conflict:{relative}"
            raise ValueError(message)
        return rendered[0], False
    if owner == "taplo":
        binary = (
            node or str(resolve_node_runtime().executable),
            str(product_node_module("@taplo/cli") / "dist/cli.js"),
        )
        rendered = tuple(
            _run(
                root,
                (
                    *binary,
                    "format",
                    "--config",
                    config,
                    "--no-auto-config",
                    "--stdin-filepath",
                    relative,
                    "-",
                ),
                content,
            )
            for config in native_configurations(root, "taplo", ".config/checks/taplo/taplo.toml")
        )
        if any(value != rendered[0] for value in rendered[1:]):
            message = f"native_formatter_policy_conflict:{relative}"
            raise ValueError(message)
        return rendered[0], False
    if owner == "shfmt":
        command = (
            str(scripts / ("shfmt.exe" if os.name == "nt" else "shfmt")),
            "--apply-ignore",
            "--filename",
            relative,
        )
    elif owner == "svgo":
        command = (
            node or str(resolve_node_runtime().executable),
            str(product_node_module("svgo") / "bin/svgo.js"),
            "--multipass",
            "--pretty",
            "--indent",
            "2",
            "--eol",
            "lf",
            "--final-newline",
            "--input",
            "-",
            "--output",
            "-",
        )
    else:
        message = f"native_formatter_unavailable:{owner}"
        raise ValueError(message)
    return _run(root, command, content), False


def prepare_source_format(root: Path, *, paths: tuple[str, ...] = ()) -> tuple[FormattedFile, ...]:
    """Prepare all selected files first; native refusal leaves every source byte untouched.

    The complete authored-text selection is validated before any formatter reads it.
    """
    authored = authored_source_files(root, paths=paths)
    selected = _selected_files(root, paths, authored)
    if invalid := authored_text_gaps(root, authored_text_files(root, authored)):
        raise ValueError(invalid[0])
    return _postimages(root, selected)


def _postimages(root: Path, selected: tuple[tuple[str, str], ...]) -> tuple[FormattedFile, ...]:
    prepared = []
    node = (
        str(resolve_node_runtime().executable)
        if any(owner in _NODE_FORMATTERS for _relative, owner in selected)
        else None
    )
    clean = _checked_clean(root, selected, node)
    for relative, owner in selected:
        path = root / relative
        before, mode = path.read_bytes(), stat.S_IMODE(path.stat().st_mode)
        after, ignored = (
            (before, False)
            if relative in clean
            else render_source_content(root, relative, owner, before, node=node)
        )
        prepared.append(FormattedFile(relative, before, after, mode, ignored))
    return tuple(prepared)


def _checked_clean(
    root: Path, selected: tuple[tuple[str, str], ...], node: str | None
) -> frozenset[str]:
    """Return the paths that every configuration's native check run leaves unchanged.

    Each formatter checks its files in as few native runs as a command line allows. A run that
    reports drift, warns or fails leaves its files to the per-file rendering, so every postimage,
    conflict and diagnostic stays the one the native formatter gives for that file alone.
    """
    clean: set[str] = set()
    for owner in sorted({owner for _relative, owner in selected}):
        checks = _native_checks(root, owner, node)
        files = [
            relative
            for relative, candidate in selected
            if candidate == owner and checks and _checkable(root, owner, relative)
        ]
        for chunk in _chunks(files):
            passed = set(chunk)
            for check in checks:
                passed &= _checked_paths(root, owner, (*check, *chunk), chunk)
            clean.update(passed)
    return frozenset(clean)


def _native_checks(root: Path, owner: str, node: str | None) -> tuple[tuple[str, ...], ...]:
    """Return one native check command per configuration, or none when files must render alone."""
    if owner == "prettier":
        prettier = (
            node or str(resolve_node_runtime().executable),
            str(product_node_module("prettier") / "bin/prettier.cjs"),
        )
        return tuple(
            (
                *prettier,
                "--list-different",
                "--config",
                config,
                "--no-editorconfig",
                "--prose-wrap",
                "preserve",
                "--ignore-path",
                os.devnull,
            )
            for config in native_configurations(
                root, "prettier", ".config/checks/prettier/prettier.toml"
            )
        )
    if owner == "ruff":
        return tuple(
            (
                str(find_ruff_bin()),
                "format",
                "--check",
                "--no-cache",
                "--no-respect-gitignore",
                "--config",
                config,
                "--",
            )
            for config in native_configurations(root, "ruff", ".config/checks/ruff/ruff.toml")
        )
    if owner == "taplo":
        configurations = native_configurations(root, "taplo", ".config/checks/taplo/taplo.toml")
        # Taplo filters named files by include and exclude, and matches rules against their
        # full paths, which stdin rendering by a relative path does not; such policies render alone.
        if any(_selects_paths(config) for config in configurations):
            return ()
        taplo = (
            node or str(resolve_node_runtime().executable),
            str(product_node_module("@taplo/cli") / "dist/cli.js"),
        )
        return tuple(
            (*taplo, "format", "--check", "--config", config, "--no-auto-config")
            for config in configurations
        )
    return ()


def _selects_paths(config: str) -> bool:
    policy = tomllib.loads(Path(config).read_text(encoding="utf-8"))
    return any(key in policy for key in ("include", "exclude", "rule"))


def _checkable(root: Path, owner: str, relative: str) -> bool:
    """Return whether a named path reaches the native check exactly as it reaches rendering."""
    if _PATTERN_CHARACTERS & set(relative):
        return False
    if owner != "prettier":
        return True
    # Prettier's check skips these directories, and its ignore decision needs the per-file query.
    parts = {*Path(relative).parts, *(root / relative).resolve().parts}
    return (
        native_repository_configuration(root, "prettier-ignore") is None
        and not parts & _PRETTIER_SKIPPED_DIRECTORIES
    )


def _chunks(paths: list[str]) -> list[tuple[str, ...]]:
    chunks: list[tuple[str, ...]] = []
    current: list[str] = []
    size = 0
    for path in paths:
        if current and size + len(path) + 1 > _CHECK_ARGUMENT_BUDGET:
            chunks.append(tuple(current))
            current, size = [], 0
        current.append(path)
        size += len(path) + 1
    return [*chunks, tuple(current)] if current else chunks


def _checked_paths(
    root: Path, owner: str, command: tuple[str, ...], chunk: tuple[str, ...]
) -> set[str]:
    """Return the paths of one chunk that its native check run leaves unchanged."""
    try:
        completed = run_command(
            root,
            command,
            text=False,
            timeout=30,
            env={"NODE_DISABLE_COMPILE_CACHE": "1"},
            remove_env=("NODE_COMPILE_CACHE", "NODE_OPTIONS", "NODE_PATH", "TAPLO_CONFIG"),
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return set()
    if owner == "taplo":
        # Taplo exits cleanly when it collects no file, so its run vouches only for a chunk it
        # reports collecting whole. It globs each named path, so a name holding a backslash, and
        # on Windows hosted conformance every name, reaches no file.
        collected = _TAPLO_COLLECTED.findall(_ANSI_ESCAPE.sub(b"", completed.stderr))
        whole = [(str(len(chunk)).encode(), b"0")]
        return set(chunk) if completed.returncode == 0 and collected == whole else set()
    if owner != "prettier":
        return set(chunk) if completed.returncode == 0 else set()
    # Prettier lists each drifting path on stdout and warns on stderr, which rendering refuses.
    listed = {line.strip().replace("\\", "/") for line in completed.stdout.decode().splitlines()}
    if completed.stderr or completed.returncode not in (0, 1) or not listed <= set(chunk) | {""}:
        return set()
    return set(chunk) - listed


def source_format_report(root: Path, *, paths: tuple[str, ...] = ()) -> dict[str, object]:
    """Check the same native postimages used by the admitted fix operation.

    Malformed authored text is reported before any native postimage is prepared.
    """
    try:
        authored = authored_source_files(root, paths=paths)
        selected = _selected_files(root, paths, authored)
        invalid = authored_text_gaps(root, authored_text_files(root, authored))
        prepared = () if invalid else _postimages(root, selected)
        changed = [item.path for item in prepared if item.before != item.after]
        gaps = invalid or [f"source_format_drift:{path}" for path in changed]
        return {
            "id": "source-format",
            "verdict": "block" if gaps else "pass",
            "state": "failed" if gaps else "passed",
            "files": [relative for relative, _owner in selected],
            "file_count": len(selected),
            "changed_paths": changed,
            "ignored_paths": [item.path for item in prepared if item.ignored],
            "required_gaps": gaps,
        }
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        return source_format_failure(root, error)


def source_format_failure(root: Path, error: Exception) -> dict[str, object]:
    """Project unavailable native input distinctly from known format or policy refusal."""
    result = {
        "id": "source-format",
        "verdict": "unknown" if isinstance(error, FileNotFoundError) else "block",
        "state": "input_unavailable" if isinstance(error, FileNotFoundError) else "blocked",
        "required_gaps": [str(error)],
        "files": [],
        "changed_paths": [],
        "file_count": 0,
    }
    if isinstance(error, GitExecutionError) or (
        isinstance(error, subprocess.CalledProcessError) and "ls-files" in error.cmd
    ):
        result.update(quality_inventory_failure(root, "source-format", error))
    elif isinstance(error, subprocess.CalledProcessError):
        result["errors"] = [
            {
                "command": list(error.cmd),
                "cwd": str(root),
                "exit_code": error.returncode,
                "stdout": error.stdout.decode(errors="replace")
                if isinstance(error.stdout, bytes)
                else error.stdout or "",
                "stderr": error.stderr.decode(errors="replace")
                if isinstance(error.stderr, bytes)
                else error.stderr or "",
            }
        ]
    return result
