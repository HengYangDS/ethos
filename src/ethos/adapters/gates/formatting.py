"""Prepare exact native formatter postimages without writing repository source."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ruff import find_ruff_bin

import ethos.adapters.gates.native.inputs as native_inputs
from ethos.adapters.gates.format_checks import checked_clean
from ethos.adapters.gates.format_checks import native_run
from ethos.adapters.gates.format_checks import repository_ignored
from ethos.adapters.gates.native.inputs import authored_source_files
from ethos.adapters.gates.native.inputs import authored_text_files
from ethos.adapters.gates.native.inputs import authored_text_gaps
from ethos.adapters.gates.native.inputs import format_ownership
from ethos.adapters.gates.native.inputs import kept_record_files
from ethos.adapters.gates.native.inputs import native_configurations
from ethos.adapters.gates.native.inputs import native_repository_configuration
from ethos.adapters.gates.native.inputs import quality_inventory_failure
from ethos.adapters.process import command_outcome
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.runtime.filesystem import runtime_scripts
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.repository.paradigm.markdown_spacing import canonical_spacing
from ethos.repository.paradigm.text_layout import canonical_text
from ethos.repository.policy.quality.format_selection import POLICY_PATH
from ethos.repository.policy.quality.format_selection import canonical_text_paths
from ethos.repository.release.resources import canonical_resource

if TYPE_CHECKING:
    from collections.abc import Iterator

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
# The repository owns the layout of text that no native formatter owns.
CANONICAL_TEXT = "repository-canonical-text"
_FORMATTED = frozenset({"native-formatter", "canonical-text"})


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
    canonical = canonical_text_paths(
        tuple(requested or authored), canonical_resource(POLICY_PATH.as_posix())
    )
    files = [
        relative
        for relative in requested or authored
        if _candidate_path(
            root,
            relative,
            excluded=relative not in selected_paths,
            explicit=bool(requested),
            canonical=relative in canonical,
        )
    ]
    ownership = format_ownership(root, tuple(dict.fromkeys(files)))
    if ownership["verdict"] != "pass":
        raise ValueError(str(ownership["failures"]))
    selected = []
    for item in ownership["assignments"]:
        if item["mutation_policy"] not in _FORMATTED:
            if requested:
                message = f"source_format_other_owner:{item['path']}"
                raise ValueError(message)
            continue
        selected.append((item["path"], item["format_owner"]))
    return tuple(selected)


def _candidate_path(
    root: Path, relative: str, *, excluded: bool, explicit: bool, canonical: bool = False
) -> bool:
    raw, path = Path(relative), root / relative
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        message = f"source_format_path_invalid:{relative}"
        raise ValueError(message)
    if excluded or (raw.suffix.lower() not in _SUFFIXES and not canonical):
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
    completed = native_run(root, command, content)
    if completed.returncode or (reject_diagnostics and completed.stderr):
        raise subprocess.CalledProcessError(
            completed.returncode, command, completed.stdout, completed.stderr
        )
    return completed.stdout


def _prettier(
    root: Path,
    relative: str,
    content: bytes,
    *,
    repository_policy: bool,
    node: str | None,
    files: tuple[str, ...] | None,
) -> tuple[bytes, bool]:
    binary = (
        node or str(resolve_node_runtime().executable),
        str(product_node_module("prettier") / "bin/prettier.cjs"),
    )
    ignore = (
        native_repository_configuration(root, "prettier-ignore", files=files)
        if repository_policy
        else None
    )
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
        native_configurations(
            root, "prettier", ".config/checks/prettier/prettier.toml", files=files
        )
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
    return list_spacing(relative, rendered[0]), False


def list_spacing(relative: str, content: bytes) -> bytes:
    """Apply the paradigm's Markdown list rule to a Markdown postimage; other text is kept."""
    if not relative.endswith(".md"):
        return content
    return canonical_spacing(content.decode("utf-8")).encode("utf-8")


def render_source_content(
    root: Path,
    relative: str,
    owner: str,
    content: bytes,
    *,
    repository_policy: bool = True,
    node: str | None = None,
    source_files: tuple[str, ...] | None = None,
) -> tuple[bytes, bool]:
    """Render one original native postimage for authored checks or owned projections.

    Callers that render many files pass ``node``, one resolved Node executable, and
    ``source_files``, the repository's source files listed once.
    """
    if owner == "prettier":
        return _prettier(
            root,
            relative,
            content,
            repository_policy=repository_policy,
            node=node,
            files=source_files,
        )
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
            for config in native_configurations(
                root, "ruff", ".config/checks/ruff/ruff.toml", files=source_files
            )
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
            for config in native_configurations(
                root, "taplo", ".config/checks/taplo/taplo.toml", files=source_files
            )
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


def prepare_source_format(
    root: Path, *, paths: tuple[str, ...] = (), kept: tuple[str, ...] | list[str] = ()
) -> tuple[FormattedFile, ...]:
    """Prepare all selected files first; native refusal leaves every source byte untouched.

    The complete authored-text selection is validated before any formatter reads it. A repair
    names the record files it keeps, and no formatter reads them.
    """
    authored = authored_source_files(root, paths=paths)
    held = frozenset(kept)
    selected = tuple(item for item in _selected_files(root, paths, authored) if item[0] not in held)
    if invalid := authored_text_gaps(root, authored_text_files(root, authored)):
        raise ValueError(invalid[0])
    try:
        return _postimages(root, selected)
    except PostimageRefusalError as refusal:
        # A repair applies nothing on any refusal: the native command's own failure stays the
        # one its caller catches, and no partial postimage escapes.
        native = refusal.refusal
        if native is None:
            raise
    # Raised outside the handler, so the native failure keeps the cause it came with.
    raise native


def source_postimages(
    root: Path, selected: tuple[tuple[str, str], ...], *, node: str | None = None
) -> tuple[FormattedFile, ...]:
    """Prepare the postimages of files whose formatter owners the caller has resolved.

    A caller that has resolved the Node executable passes it as ``node``.
    """
    return _postimages(root, selected, node)


def _postimages(
    root: Path, selected: tuple[tuple[str, str], ...], node: str | None = None
) -> tuple[FormattedFile, ...]:
    """Prepare each file's postimage; a refusal carries the ones prepared before it.

    A refusal anywhere in the selection keeps the postimages already prepared, so a caller that
    reports drift names those files beside the refusal instead of the refusal alone.
    """
    prepared: list[FormattedFile] = []
    try:
        prepared.extend(_each_postimage(root, selected, node))
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        if not prepared:
            raise
        raise PostimageRefusalError(str(error), tuple(prepared)) from error
    return tuple(prepared)


def _each_postimage(
    root: Path, selected: tuple[tuple[str, str], ...], node: str | None
) -> Iterator[FormattedFile]:
    # One listing of the repository serves every file: a configuration is a fact of the tree.
    files = tuple(native_inputs.quality_source_files(root))
    node = node or (
        str(resolve_node_runtime().executable)
        if any(owner in _NODE_FORMATTERS for _relative, owner in selected)
        else None
    )
    excluded = repository_ignored(root, selected, node, files)
    clean = checked_clean(root, selected, node, files, excluded)
    for relative, owner in selected:
        path = root / relative
        before, mode = path.read_bytes(), stat.S_IMODE(path.stat().st_mode)
        if owner == CANONICAL_TEXT:
            after, ignored = canonical_text(before.decode("utf-8")).encode("utf-8"), False
        elif excluded is not None and owner == "prettier" and relative in excluded:
            after, ignored = before, True
        else:
            after, ignored = (
                (list_spacing(relative, before) if owner == "prettier" else before, False)
                if relative in clean
                else render_source_content(
                    root, relative, owner, before, node=node, source_files=files
                )
            )
        yield FormattedFile(relative, before, after, mode, ignored)


class PostimageRefusalError(ValueError):
    """A postimage preparation refused after some files were prepared; their results survive."""

    def __init__(self, reason: str, prepared: tuple[FormattedFile, ...]) -> None:
        super().__init__(reason)
        self.prepared = prepared

    @property
    def refusal(self) -> Exception | None:
        """The error that stopped the preparation; its own report keeps the diagnostics."""
        return self.__cause__ if isinstance(self.__cause__, Exception) else None


def source_format_report(root: Path, *, paths: tuple[str, ...] = ()) -> dict[str, object]:
    """Check the same native postimages used by the admitted fix operation.

    Malformed authored text is reported before any native postimage is prepared.
    """
    try:
        authored = authored_source_files(root, paths=paths)
        selected = _selected_files(root, paths, authored)
        invalid = authored_text_gaps(root, authored_text_files(root, authored))
        prepared = () if invalid else _postimages(root, selected)
        base, kept = kept_record_files(root, paths)
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
            "record_base": base,
            "record_paths": kept,
            "required_gaps": gaps,
        }
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        return source_format_failure(root, error)


def source_format_failure(root: Path, error: Exception) -> dict[str, object]:
    """Project unavailable native input distinctly from known format or policy refusal."""
    if isinstance(error, PostimageRefusalError) and error.refusal is not None:
        # The cause's own report is the one with the diagnostics; the wrapper only carries it.
        error = error.refusal
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
        result["errors"] = [command_outcome(error, cwd=root)]
    return result
