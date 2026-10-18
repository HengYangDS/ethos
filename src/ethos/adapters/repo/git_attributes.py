"""Native Git attribute observations of a repository's tracked paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from pathlib import Path

_RECEIVED_ATTRIBUTES = (b"linguist-vendored", b"linguist-generated")


def received_paths(root: Path, paths: tuple[str, ...]) -> frozenset[str]:
    """Return the paths whose native Git attributes mark them vendored or generated.

    Their names are received from upstream or a generator, not authored here. An
    unavailable or malformed observation receives nothing, so every name stays judged.
    """
    if not paths:
        return frozenset()
    completed = run_git(
        root,
        "check-attr",
        "-z",
        "--stdin",
        *(attribute.decode() for attribute in _RECEIVED_ATTRIBUTES),
        stdin=b"".join(path.encode("utf-8", errors="surrogateescape") + b"\0" for path in paths),
        check=False,
        text=False,
        observation=True,
    )
    fields = completed.stdout.split(b"\0")
    if (
        completed.returncode
        or fields.pop() != b""
        or len(fields) != 3 * len(_RECEIVED_ATTRIBUTES) * len(paths)
    ):
        return frozenset()
    return frozenset(
        fields[index].decode("utf-8", errors="surrogateescape")
        for index in range(0, len(fields), 3)
        if fields[index + 1] in _RECEIVED_ATTRIBUTES and fields[index + 2] in {b"set", b"true"}
    )
