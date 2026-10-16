"""Select authored carriers, render native candidates and apply exact admitted bytes."""

from __future__ import annotations

import difflib
import hashlib
import os
import shlex
import tempfile
import tomllib
from collections import defaultdict
from pathlib import Path
from pathlib import PurePosixPath
from pathlib import PureWindowsPath
from stat import S_IMODE
from typing import NamedTuple

import yaml
from yaml.nodes import MappingNode
from yaml.nodes import Node
from yaml.nodes import ScalarNode
from yaml.nodes import SequenceNode

from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.gates.format_selection import audit
from ethos.adapters.gates.tool import format_source_contents
from ethos.adapters.repo.content.observation import read_regular_bytes
from ethos.adapters.repo.git import git_files
from ethos.adapters.repo.git import run_git
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence


class SourceEdit(NamedTuple):
    """One literal source snapshot and its native candidate, including file mode."""

    path: str
    before: bytes
    after: bytes
    mode: int


_FORMAT_SUFFIXES = {"prettier": (".md", ".yaml", ".yml"), "taplo": (".toml",)}


def _read(root: Path, relative: str) -> bytes:
    return read_regular_bytes(
        root,
        relative,
        unsafe_gap=f"format_source_unsafe:{relative}",
        unstable_gap=f"format_source_stale:{relative}",
        size_gap=f"format_source_too_large:{relative}",
    )


def _coordinates(root: Path) -> tuple[bytes, bytes]:
    head = run_git(root, "rev-parse", "--verify", "HEAD", check=False, text=False).stdout
    index = run_git(root, "ls-files", "--stage", "-z", text=False).stdout
    return head, index


def _selection(root: Path, paths: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    tracked = tuple(git_files(root, check=True))
    for relative in paths:
        pure = PurePosixPath(relative)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or "\\" in relative
            or PureWindowsPath(relative).drive
            or pure.as_posix() != relative
            or relative not in tracked
        ):
            message = f"format_selection_invalid:{relative}"
            raise ValueError(message)
    requested = (
        tuple(dict.fromkeys(paths))
        if paths
        else tuple(
            path for path in tracked if Path(path).suffix in {".md", ".toml", ".yaml", ".yml"}
        )
    )
    ownership = audit(root, paths=requested)
    if ownership["failures"]:
        message = f"format_ownership_unresolved:{ownership['failures']}"
        raise ValueError(message)
    selected = []
    for assignment in ownership["assignments"]:
        relative, owner = assignment["path"], assignment["format_owner"]
        if assignment["mutation_policy"] == "native-formatter" and Path(
            relative
        ).suffix in _FORMAT_SUFFIXES.get(owner, ()):
            selected.append((relative, owner))
        elif paths:
            message = f"format_source_has_another_owner:{relative}:{assignment['format_command']}"
            raise ValueError(message)
    return tuple(selected)


def _edits(root: Path, selected: tuple[tuple[str, str], ...]) -> tuple[SourceEdit, ...]:
    groups: dict[str, dict[str, bytes]] = defaultdict(dict)
    for relative, owner in selected:
        groups[owner][relative] = _read(root, relative)
    rendered = {
        relative: content
        for owner, sources in groups.items()
        for relative, content in format_source_contents(root, owner, sources).items()
    }
    for relative, owner in selected:
        before, after = groups[owner][relative], rendered[relative]
        suffix = Path(relative).suffix
        if suffix == ".toml":
            unchanged = _toml_value(tomllib.loads(before.decode())) == _toml_value(
                tomllib.loads(after.decode())
            )
        elif suffix in {".yaml", ".yml"}:
            unchanged = tuple(_yaml_value(node, {}) for node in yaml.compose_all(before)) == tuple(
                _yaml_value(node, {}) for node in yaml.compose_all(after)
            )
        else:
            unchanged = True
        if not unchanged:
            message = f"format_semantics_changed:{relative}"
            raise ValueError(message)
    return tuple(
        SourceEdit(
            relative,
            groups[owner][relative],
            rendered[relative],
            S_IMODE((root / relative).stat().st_mode),
        )
        for relative, owner in selected
    )


def _toml_value(value: object) -> object:
    """Preserve native scalar types, including NaN, dates and booleans."""
    if isinstance(value, dict):
        return tuple((key, _toml_value(item)) for key, item in sorted(value.items()))
    if isinstance(value, list):
        return tuple(_toml_value(item) for item in value)
    return type(value).__name__, repr(value)


def _yaml_value(node: Node, seen: dict[int, int]) -> object:
    """Compare native tagged node graphs, including aliases, without constructing objects."""
    identity = id(node)
    if identity in seen:
        return "alias", seen[identity]
    seen[identity] = len(seen)
    if isinstance(node, ScalarNode):
        return node.tag, node.value
    if isinstance(node, SequenceNode):
        return node.tag, tuple(_yaml_value(child, seen) for child in node.value)
    if isinstance(node, MappingNode):
        return node.tag, tuple(
            (_yaml_value(key, seen), _yaml_value(value, seen)) for key, value in node.value
        )
    message = "format_yaml_node_invalid"
    raise ValueError(message)


def _replace(root: Path, edit: SourceEdit, *, restore: bool = False) -> None:
    expected, candidate = (edit.after, edit.before) if restore else (edit.before, edit.after)
    if _read(root, edit.path) != expected:
        message = f"format_source_stale:{edit.path}"
        raise ValueError(message)
    target = root / edit.path
    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(candidate)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(edit.mode)
        if _read(root, edit.path) != expected:
            message = f"format_source_stale:{edit.path}"
            raise ValueError(message)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _require_stable(
    root: Path,
    coordinates: tuple[bytes, bytes],
    edits: tuple[SourceEdit, ...],
    *,
    postimage: bool = False,
) -> None:
    """Reobserve the complete selected source and Git index at each operation boundary."""
    if _coordinates(root) != coordinates or any(
        _read(root, edit.path) != (edit.after if postimage else edit.before) for edit in edits
    ):
        message = "format_source_observation_stale"
        raise ValueError(message)


def _execute_format(
    repo: Path,
    paths: tuple[str, ...],
    *,
    check: bool,
    apply: bool,
    report: dict[str, object],
    written: list[SourceEdit],
) -> dict[str, object]:
    """Render, inspect and admit one selected candidate before its native source effect."""
    if check and apply:
        message = "format_check_and_apply_conflict"
        raise ValueError(message)
    coordinates = _coordinates(repo)
    selected = _selection(repo, paths)
    edits = _edits(repo, selected)
    changed = tuple(edit for edit in edits if edit.before != edit.after)
    report.update(
        selected_paths=[edit.path for edit in edits],
        changed_paths=[edit.path for edit in changed],
        edits=[
            {
                "path": edit.path,
                "before_sha256": hashlib.sha256(edit.before).hexdigest(),
                "after_sha256": hashlib.sha256(edit.after).hexdigest(),
                "diff": "".join(
                    difflib.unified_diff(
                        edit.before.decode().splitlines(keepends=True),
                        edit.after.decode().splitlines(keepends=True),
                        fromfile=f"a/{edit.path}",
                        tofile=f"b/{edit.path}",
                    )
                ),
            }
            for edit in changed
        ],
    )
    _require_stable(repo, coordinates, edits)
    if not changed:
        report["state"] = "conforming" if selected else "not_applicable"
        return report
    report["next_action"] = shlex.join(
        ("ethos", "format", *paths, "--apply", "--root", str(repo), "--json")
    )
    if check:
        report.update(
            verdict="block",
            state="format_required",
            required_gaps=[f"format_required:{edit.path}" for edit in changed],
        )
        return report
    if not apply:
        return report
    admission = prewrite_guard(
        root=repo,
        paths=[repo / edit.path for edit in changed],
        editor_root=repo,
        require_editor_root=True,
    )
    verdict = report_verdict(admission)
    if verdict != "pass":
        report.update(
            verdict=verdict,
            state="admission_refused",
            required_gaps=string_sequence(admission.get("required_gaps"))
            or ["format_write_not_admitted"],
        )
        return report
    _require_stable(repo, coordinates, edits)
    for edit in changed:
        _replace(repo, edit)
        written.append(edit)
    _require_stable(repo, coordinates, edits, postimage=True)
    report.update(state="formatted", applied=True, next_action="")
    return report


def format_sources(
    *,
    root: Path,
    paths: tuple[str, ...] = (),
    check: bool = False,
    apply: bool = False,
) -> dict[str, object]:
    """Never infer write permission from rendering or accept an incomplete source effect."""
    repo = root.resolve()
    report: dict[str, object] = {
        "verdict": "pass",
        "state": "planned",
        "applied": False,
        "selected_paths": [],
        "changed_paths": [],
        "edits": [],
        "required_gaps": [],
    }
    written: list[SourceEdit] = []
    try:
        return _execute_format(
            repo, paths, check=check, apply=apply, report=report, written=written
        )
    except (OSError, UnicodeError, ValueError) as error:
        gaps = [str(error)]
        for edit in reversed(written):
            try:
                _replace(repo, edit, restore=True)
            except (OSError, ValueError) as restore_error:
                gaps.append(str(restore_error))
        report.update(
            verdict="unknown" if "unavailable" in str(error) else "block",
            state="unproven",
            required_gaps=gaps,
            applied=False,
        )
        return report
