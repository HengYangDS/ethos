"""Build and observe native Git patch identities without applying source effects."""

from __future__ import annotations

import ast
import difflib
import json
import string
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator
    from pathlib import Path


def unified_patch(changes: Iterable[tuple[str, bytes, bytes]]) -> str:
    """Return one `git apply` patch that turns each path's UTF-8 preimage into its postimage."""
    parts = []
    for path, before, after in changes:
        if before == after:
            continue
        left, right = "a/" + path, "b/" + path
        lines = difflib.unified_diff(
            before.decode("utf-8").splitlines(keepends=True),
            after.decode("utf-8").splitlines(keepends=True),
            fromfile=left,
            tofile=right,
        )
        patch = list(lines)
        patch[:2] = [
            f"--- {json.dumps(left, ensure_ascii=False)}\n",
            f"+++ {json.dumps(right, ensure_ascii=False)}\n",
        ]
        material = [
            line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
            for line in patch
        ]
        parts.append(
            "diff --git "
            f"{json.dumps(left, ensure_ascii=False)} {json.dumps(right, ensure_ascii=False)}\n"
            + "".join(material)
        )
    return "".join(parts)


def unified_patch_changes(root: Path, patch: str) -> tuple[list[dict[str, object]], str]:
    """Name each entry's path, the name that Git reports for it, and its preimage's place.

    What a patch does at a path (a creation, a deletion, a kind of file) is no reading of
    its text: a caller observes it from Git, where the patch is applied. Unsupported or
    malformed native input is refused.
    """
    if any(line.startswith(("GIT binary patch", "Binary files ")) for line in patch.splitlines()):
        return [], "prewrite_patch_binary_unsupported"
    native = run_git(
        root,
        "apply",
        "--numstat",
        "--unsafe-paths",
        "-z",
        "-",
        stdin=patch.encode("utf-8"),
        text=False,
        check=False,
    )
    if native.returncode:
        return [], "prewrite_patch_invalid"
    paths = tuple(
        record.split(b"\t", 2)[2].decode("utf-8") for record in native.stdout.split(b"\0") if record
    )
    changes: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in _header_lines(patch):
        if line.startswith("diff --git "):
            if len(changes) >= len(paths):
                return changes, "prewrite_patch_invalid"
            path = paths[len(changes)]
            current = {"old_path": path, "path": path, "reported": path}
            changes.append(current)
        elif current is not None:
            try:
                _update_patch_change(current, line)
            except (ValueError, TypeError, SyntaxError):
                return changes, "prewrite_patch_invalid"
    if not changes or len(changes) != len(paths) or any(not change["path"] for change in changes):
        return changes, "prewrite_patch_invalid"
    return changes, ""


# The lines that Git reads as an entry's extended header; the header ends at the first other line.
_HEADER = (
    "--- ",
    "+++ ",
    "old mode ",
    "new mode ",
    "deleted file mode ",
    "new file mode ",
    "copy from ",
    "copy to ",
    "rename old ",
    "rename new ",
    "rename from ",
    "rename to ",
    "similarity index ",
    "dissimilarity index ",
    "index ",
)


def _header_lines(patch: str) -> Iterator[str]:
    """Yield each entry's `diff --git` line and the header lines that follow it at once.

    Git ends a line at a line feed, reads a carriage return before it as white space, and ends
    an entry's header at the first line that is none of its header lines; a hunk's content and
    the text after an entry are read by no caller.
    """
    in_header = False
    for raw in patch.split("\n"):
        line = raw.removesuffix("\r")
        in_header = line.startswith("diff --git ") or (in_header and line.startswith(_HEADER))
        if in_header:
            yield line


def _update_patch_change(change: dict[str, object], line: str) -> None:
    """Read where the entry's preimage lies; Git's own report names the entry's path."""
    if line.startswith("--- "):
        # A name with nothing after its first component names no file to Git, which then keeps
        # the name of the entry's first line.
        change["old_path"] = _file_line_path(line) or change["old_path"]
    elif line.startswith("+++ "):
        # A deletion written without its `deleted file mode` line: Git reports the null path
        # as the entry's name. The entry is named by its preimage, as a deletion of it.
        if _file_line_path(line) == "/dev/null":
            change["path"] = change["old_path"]
    elif line.startswith(("rename from ", "rename old ", "copy from ")):
        # Git writes these names whole, without the component that a file line carries.
        change["old_path"] = _unquoted(line.split(" ", 2)[2])
    elif line.startswith("new file mode "):
        # Git writes no `---` and `+++` lines for an entry without content.
        change["old_path"] = "/dev/null"


def _file_line_path(line: str) -> str:
    """Return the name of a `---` or `+++` line without its first component, as Git reads it."""
    name = _unquoted(line[4:].split("\t", 1)[0])
    return name if name == "/dev/null" else name.partition("/")[2]


def _unquoted(raw: str) -> str:
    """Return a name as written, or the name that Git's quoting stands for.

    Git ends a name that is not quoted at its first carriage return.
    """
    if not raw.startswith('"'):
        return raw.partition("\r")[0]
    decoded = ast.literal_eval(raw)
    if not isinstance(decoded, str):
        message = "prewrite_patch_path_invalid"
        raise TypeError(message)
    if any(f"\\{digit}" in raw for digit in string.octdigits):
        return decoded.encode("latin-1").decode("utf-8")
    return decoded
