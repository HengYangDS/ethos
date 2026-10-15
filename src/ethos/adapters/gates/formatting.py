"""Prepare exact native formatter postimages without writing repository source."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ruff import find_ruff_bin

from ethos.adapters.gates.native.inputs import authored_source_files
from ethos.adapters.gates.native.inputs import native_configurations
from ethos.adapters.gates.native.inputs import quality_inventory_failure
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.runtime.filesystem import runtime_scripts
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.repository.policy.quality.format_selection import audit
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


@dataclass(frozen=True)
class FormattedFile:
    """One literal path, original content and native postimage with preserved mode."""

    path: str
    before: bytes
    after: bytes
    mode: int
    ignored: bool = False


def _selected_files(root: Path, requested: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    authored = authored_source_files(root, paths=requested)
    selected_paths = set(authored)
    files = [
        relative
        for relative in requested or authored
        if _candidate_path(
            root, relative, excluded=relative not in selected_paths, explicit=bool(requested)
        )
    ]
    ownership = audit(
        root,
        paths=tuple(dict.fromkeys(files)),
        configuration=canonical_resource(".config/checks/format-selection/policy.toml"),
    )
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
        remove_env=("NODE_OPTIONS", "NODE_PATH", "TAPLO_CONFIG"),
    )
    if completed.returncode or (reject_diagnostics and completed.stderr):
        raise subprocess.CalledProcessError(
            completed.returncode, command, completed.stdout, completed.stderr
        )
    return completed.stdout


def _prettier(
    root: Path, relative: str, content: bytes, *, repository_policy: bool
) -> tuple[bytes, bool]:
    binary = (
        str(resolve_node_runtime().executable),
        str(product_node_module("prettier") / "bin/prettier.cjs"),
    )
    ignore = root / ".prettierignore"
    if repository_policy and ignore.is_symlink():
        message = "native_formatter_ignore_invalid"
        raise ValueError(message)
    ignored = (
        repository_policy
        and json.loads(
            _run(
                root,
                (
                    *binary,
                    "--ignore-path",
                    str(ignore) if ignore.is_file() else os.devnull,
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
) -> tuple[bytes, bool]:
    """Render one original native postimage for authored checks or owned projections."""
    if owner == "prettier":
        return _prettier(root, relative, content, repository_policy=repository_policy)
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
            str(resolve_node_runtime().executable),
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
            str(resolve_node_runtime().executable),
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
    """Prepare all selected files first; native refusal leaves every source byte untouched."""
    prepared = []
    for relative, owner in _selected_files(root, paths):
        path = root / relative
        before, mode = path.read_bytes(), stat.S_IMODE(path.stat().st_mode)
        after, ignored = render_source_content(root, relative, owner, before)
        prepared.append(FormattedFile(relative, before, after, mode, ignored))
    return tuple(prepared)


def source_format_report(root: Path, *, paths: tuple[str, ...] = ()) -> dict[str, object]:
    """Check the same native postimages used by the admitted fix operation."""
    try:
        prepared = prepare_source_format(root, paths=paths)
        changed = [item.path for item in prepared if item.before != item.after]
        return {
            "id": "source-format",
            "verdict": "block" if changed else "pass",
            "state": "failed" if changed else "passed",
            "files": [item.path for item in prepared],
            "file_count": len(prepared),
            "changed_paths": changed,
            "ignored_paths": [item.path for item in prepared if item.ignored],
            "required_gaps": [f"source_format_drift:{path}" for path in changed],
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
