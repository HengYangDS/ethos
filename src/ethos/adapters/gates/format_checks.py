"""Ask each native formatter, in as few runs as a command line allows, which files are clean.

The format gate renders a file alone only when no native check run vouches for it. This module
owns those runs: which files a repository's Prettier ignore file excludes, and which of the
rest every configuration's check leaves unchanged.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tomllib
from pathlib import Path
from typing import override

from ruff import find_ruff_bin

from ethos.adapters.gates.native.inputs import native_configurations
from ethos.adapters.gates.native.inputs import native_repository_configuration
from ethos.adapters.process import run_command
from ethos.adapters.process import stream_text
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.repository.paradigm.parameters import seconds

# A named path that a formatter could read as a pattern is rendered alone.
_PATTERN_CHARACTERS = frozenset("*?[]{}")
_PRETTIER_SKIPPED_DIRECTORIES = frozenset({".git", ".hg", ".jj", ".sl", ".svn", "node_modules"})
# Paths per native check run stay far below a host's command-line limit.
_CHECK_ARGUMENT_BUDGET = 6000
_TAPLO_COLLECTED = re.compile(rb"found files total=(\d+) excluded=(\d+)")
_ANSI_ESCAPE = re.compile(rb"\x1b\[[0-9;]*m")


class _IgnoreQueryError(subprocess.CalledProcessError):
    """A failed ignore query, whose text carries what the tool wrote to standard error."""

    @override
    def __str__(self) -> str:
        return f"{super().__str__()} {stream_text(self.stderr)}".strip()


def native_run(
    root: Path, command: tuple[str, ...], content: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run one native command with the environment that every such run shares."""
    return run_command(
        root,
        command,
        stdin=content,
        text=False,
        timeout=seconds("tool"),
        env={"NODE_DISABLE_COMPILE_CACHE": "1"},
        remove_env=("NODE_COMPILE_CACHE", "NODE_OPTIONS", "NODE_PATH", "TAPLO_CONFIG"),
    )


def repository_ignored(
    root: Path, selected: tuple[tuple[str, str], ...], node: str | None, files: tuple[str, ...]
) -> frozenset[str] | None:
    """Return the Prettier files that the repository's ignore file excludes, or None without one.

    One native run asks Prettier's own API about every file, where each file's rendering asks
    about itself alone.
    """
    named = [relative for relative, owner in selected if owner == "prettier"]
    if not named:
        return None
    ignore = native_repository_configuration(root, "prettier-ignore", files=files)
    if ignore is None or node is None:
        return None
    command = (
        node,
        str(Path(__file__).with_name("prettier-ignored.mjs")),
        str(product_node_module("prettier") / "index.mjs"),
        str(ignore),
        str(root),
    )
    listed = native_run(root, command, json.dumps(named).encode("utf-8"))
    if listed.returncode:
        raise _IgnoreQueryError(listed.returncode, command, listed.stdout, listed.stderr)
    return frozenset(json.loads(listed.stdout))


def checked_clean(
    root: Path,
    selected: tuple[tuple[str, str], ...],
    node: str | None,
    files: tuple[str, ...],
    excluded: frozenset[str] | None,
) -> frozenset[str]:
    """Return the paths that every configuration's native check run leaves unchanged.

    Each formatter checks its files in as few native runs as a command line allows. A run that
    reports drift, warns or fails leaves its files to the per-file rendering, so every postimage,
    conflict and diagnostic stays the one the native formatter gives for that file alone.
    """
    clean: set[str] = set()
    for owner in sorted({owner for _relative, owner in selected}):
        checks = _native_checks(root, owner, node, files)
        named = [
            relative
            for relative, candidate in selected
            if candidate == owner
            and checks
            and (excluded is None or relative not in excluded)
            and _checkable(root, owner, relative)
        ]
        for chunk in _chunks(named):
            passed = set(chunk)
            for check in checks:
                passed &= _checked_paths(root, owner, (*check, *chunk), chunk)
            clean.update(passed)
    return frozenset(clean)


def _native_checks(
    root: Path, owner: str, node: str | None, files: tuple[str, ...]
) -> tuple[tuple[str, ...], ...]:
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
                root, "prettier", ".config/checks/prettier/prettier.toml", files=files
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
            for config in native_configurations(
                root, "ruff", ".config/checks/ruff/ruff.toml", files=files
            )
        )
    if owner == "taplo":
        configurations = native_configurations(
            root, "taplo", ".config/checks/taplo/taplo.toml", files=files
        )
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
    """Return whether a named path reaches the native check exactly as it reaches rendering.

    The caller has taken out the files that the repository's ignore file excludes.
    """
    if _PATTERN_CHARACTERS & set(relative):
        return False
    if owner != "prettier":
        return True
    # Prettier's check skips these directories; a file under one renders alone.
    parts = {*Path(relative).parts, *(root / relative).resolve().parts}
    return not parts & _PRETTIER_SKIPPED_DIRECTORIES


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
        completed = native_run(root, command)
    except (OSError, ValueError, subprocess.SubprocessError):
        return set()
    if owner == "taplo":
        # Taplo exits cleanly when it collects no file, so its run vouches only for a chunk it
        # reports collecting whole. It globs each named path, so a name holding a backslash
        # reaches no file.
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
