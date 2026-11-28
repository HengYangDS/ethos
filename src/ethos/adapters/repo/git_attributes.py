"""Native Git attribute and text observations of a repository's paths."""

from __future__ import annotations

import os
from pathlib import PurePosixPath
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.worktree_postimage import observe_worktree_postimage

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_RECEIVED_ATTRIBUTES = (b"linguist-vendored", b"linguist-generated")
_ATTRIBUTE_FILES = (":(glob)**/.gitattributes",)
_SHA256_HEX = 64
_CHECKOUT_ATTRIBUTES = (b"text", b"eol")
_BINARY_WORKTREE = b"w/-text"


def received_paths(root: Path, paths: tuple[str, ...]) -> frozenset[str]:
    """Return the paths whose native Git attributes mark them vendored or generated.

    Their names are received from upstream or a generator, not authored here. An
    unavailable or malformed observation receives nothing, so every name stays judged.
    """
    return _marked(_native_attributes(root, paths, _RECEIVED_ATTRIBUTES))


def worktree_received_paths(root: Path, paths: tuple[str, ...]) -> frozenset[str]:
    """Return the paths that the worktree's bound `.gitattributes` files mark vendored or generated.

    The authored selection reads its marks here. Bound is what a proof's source binding sees:
    the head's tree with the worktree's `.gitattributes` files as Git would add them. Git
    resolves the marks against that tree, by exact case, through an empty Git directory of the
    reading's own. So the repository's `info/attributes`, a configured attributes file, a
    `.gitattributes` file that an exclude rule hides and the host's case rule mark nothing, and
    no attributes file is read from disk here. A name that leaves the tree receives nothing;
    its own caller names it invalid. Without a head there is no tree, and nothing is received.
    Git's refusal keeps its own error. Every other reader keeps `received_paths`; their use of
    local state is the subject of the draft Change `local-git-state-binding`.
    """
    inside = tuple(
        name
        for name in paths
        if not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
    )
    head = current_tracked_head(root) if inside else ""
    if not head:
        return frozenset()
    with (
        observe_worktree_postimage(
            root, previous=head, include_paths=False, only=_ATTRIBUTE_FILES
        ) as bound,
        TemporaryDirectory(prefix="ethos-attributes-") as empty,
    ):
        hashing = f"--object-format={'sha256' if len(head) == _SHA256_HEX else 'sha1'}"
        run_git(root, "init", "--quiet", "--bare", "--template=", hashing, empty, observation=True)
        isolated = (
            "--git-dir",
            empty,
            "-c",
            f"core.attributesFile={os.devnull}",
            "-c",
            "core.ignoreCase=false",
        )
        objects = {key: value for key, value in bound.environment.items() if "OBJECT" in key}
        observed = _native_attributes(
            root, inside, _RECEIVED_ATTRIBUTES, *isolated, source=bound.tree, objects=objects
        )
        return _marked(observed)


def checkout_line_endings(root: Path, paths: tuple[str, ...]) -> dict[str, tuple[str, str]] | None:
    """Return each path's effective `text` and `eol` attributes as native Git resolves them.

    Later and nested patterns are included. None means Git did not report every path, so
    no checkout is concluded.
    """
    observed = _native_attributes(root, paths, _CHECKOUT_ATTRIBUTES)
    if observed is None or set(observed) != set(paths):
        return None
    return {
        path: (_text(values[b"text"]), _text(values[b"eol"])) for path, values in observed.items()
    }


def binary_content_paths(root: Path, paths: tuple[str, ...]) -> frozenset[str] | None:
    """Return the paths whose worktree content Git itself classifies as binary.

    Gates read worktree bytes, so the staged copy does not decide. `git ls-files --eol`
    reports this classification apart from the `text` and `eol` attributes, which govern
    line-ending conversion: content such as a NUL byte reads `-text`, while a valid document
    that an attribute marks `-text` keeps its own reading. Git's own refusal raises its
    `CalledProcessError` with both streams; None means a successful Git classified fewer paths.
    """
    if not paths:
        return frozenset()
    completed = run_git(
        root,
        "ls-files",
        "--eol",
        "-z",
        "--cached",
        "--others",
        "--exclude-standard",
        check=False,
        text=False,
        observation=True,
    )
    completed.check_returncode()
    classified: dict[str, bool] = {}
    for record in completed.stdout.split(b"\0")[:-1]:
        info, separator, path = record.partition(b"\t")
        if not separator:
            return None
        classified[_text(path)] = _BINARY_WORKTREE in info.split()
    if not set(paths) <= set(classified):
        return None
    return frozenset(path for path in paths if classified[path])


def _marked(observed: dict[str, dict[bytes, bytes]] | None) -> frozenset[str]:
    """Name the observed paths that either attribute marks; no observation marks none."""
    return frozenset(
        path
        for path, values in (observed or {}).items()
        if any(values[name] in {b"set", b"true"} for name in _RECEIVED_ATTRIBUTES)
    )


def _native_attributes(
    root: Path,
    paths: tuple[str, ...],
    names: tuple[bytes, ...],
    *options: str,
    source: str = "",
    objects: Mapping[str, str] | None = None,
) -> dict[str, dict[bytes, bytes]] | None:
    """Return each path's named attribute values, or None unless Git reports all of them.

    Options for Git itself precede the command. A read against a source tree finds its
    objects where `objects` says, and raises Git's own refusal.
    """
    if not paths:
        return {}
    command = (*options, "check-attr", *(("--source", source) if source else ()), "-z", "--stdin")
    stdin = b"".join(path.encode("utf-8", errors="surrogateescape") + b"\0" for path in paths)
    attributes = tuple(name.decode() for name in names)
    completed = (
        run_git(root, *command, *attributes, stdin=stdin, text=False, env=objects)
        if source
        else run_git(
            root, *command, *attributes, stdin=stdin, check=False, text=False, observation=True
        )
    )
    fields = completed.stdout.split(b"\0")
    if completed.returncode or fields.pop() != b"" or len(fields) != 3 * len(names) * len(paths):
        return None
    observed: dict[str, dict[bytes, bytes]] = {}
    for index in range(0, len(fields), 3):
        path = _text(fields[index])
        observed.setdefault(path, {})[fields[index + 1]] = fields[index + 2]
    if any(set(values) != set(names) for values in observed.values()):
        return None
    return observed


def _text(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape")
