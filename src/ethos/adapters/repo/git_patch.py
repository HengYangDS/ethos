"""Observe native Git patch identities without applying source effects."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from pathlib import Path


def unified_patch_changes(root: Path, patch: str) -> tuple[list[dict[str, object]], str]:
    """Read literal text-patch identities; refuse unsupported or malformed native input."""
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
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            if len(changes) >= len(paths):
                return changes, "prewrite_patch_invalid"
            path = paths[len(changes)]
            current = {"old_path": path, "path": path, "new": False, "deleted": False}
            changes.append(current)
        elif current is not None:
            try:
                _update_patch_change(current, line)
            except (ValueError, TypeError, SyntaxError):
                return changes, "prewrite_patch_invalid"
    if not changes or len(changes) != len(paths) or any(not change["path"] for change in changes):
        return changes, "prewrite_patch_invalid"
    return changes, ""


def _update_patch_change(change: dict[str, object], line: str) -> None:
    if line.startswith("--- "):
        change["old_path"] = _patch_path(line[4:].split("\t", 1)[0])
        change["new"] = change["old_path"] == "/dev/null"
    elif line.startswith("+++ "):
        path = _patch_path(line[4:].split("\t", 1)[0])
        change["deleted"] = path == "/dev/null"
        change["path"] = change["old_path"] if change["deleted"] else path
    elif line.startswith(("rename from ", "copy from ")):
        change["old_path"] = _patch_path(line.split(" ", 2)[2])


def _patch_path(raw: str) -> str:
    if raw.startswith('"'):
        decoded = ast.literal_eval(raw)
        if not isinstance(decoded, str):
            message = "prewrite_patch_path_invalid"
            raise ValueError(message)
        raw = (
            decoded.encode("latin-1").decode("utf-8")
            if any(f"\\{digit}" in raw for digit in "01234567")
            else decoded
        )
    if raw == "/dev/null":
        return raw
    return raw.removeprefix("a/").removeprefix("b/")
