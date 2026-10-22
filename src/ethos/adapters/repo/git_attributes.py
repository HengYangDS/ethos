"""Native Git attribute and text observations of a repository's paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from pathlib import Path

_RECEIVED_ATTRIBUTES = (b"linguist-vendored", b"linguist-generated")
_CHECKOUT_ATTRIBUTES = (b"text", b"eol")
_BINARY_WORKTREE = b"w/-text"


def received_paths(root: Path, paths: tuple[str, ...]) -> frozenset[str]:
    """Return the paths whose native Git attributes mark them vendored or generated.

    Their names are received from upstream or a generator, not authored here. An
    unavailable or malformed observation receives nothing, so every name stays judged.
    """
    observed = _native_attributes(root, paths, _RECEIVED_ATTRIBUTES) or {}
    return frozenset(
        path
        for path, values in observed.items()
        if any(values[name] in {b"set", b"true"} for name in _RECEIVED_ATTRIBUTES)
    )


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
    that an attribute marks `-text` keeps its own reading. None means Git did not classify
    every path.
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
    classified: dict[str, bool] = {}
    for record in completed.stdout.split(b"\0")[:-1]:
        info, separator, path = record.partition(b"\t")
        if not separator:
            return None
        classified[_text(path)] = _BINARY_WORKTREE in info.split()
    if completed.returncode or not set(paths) <= set(classified):
        return None
    return frozenset(path for path in paths if classified[path])


def _native_attributes(
    root: Path, paths: tuple[str, ...], names: tuple[bytes, ...]
) -> dict[str, dict[bytes, bytes]] | None:
    """Return each path's named attribute values, or None unless Git reports all of them."""
    if not paths:
        return {}
    completed = run_git(
        root,
        "check-attr",
        "-z",
        "--stdin",
        *(name.decode() for name in names),
        stdin=b"".join(path.encode("utf-8", errors="surrogateescape") + b"\0" for path in paths),
        check=False,
        text=False,
        observation=True,
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
