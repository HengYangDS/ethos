"""Apply a prewrite patch to copies of its preimages, in a workspace that stands alone."""

from __future__ import annotations

import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from collections.abc import Generator


def patch_applies(root: Path, patch: str, *, check_preimage: bool = False) -> bool:
    """Check the patch in the repository, or apply it in a workspace."""
    command = ["apply", "--whitespace=error-all", "-"]
    if check_preimage:
        command.insert(2, "--check")
    # Inside another checkout Git takes a workspace for a subdirectory of that work tree, skips
    # every path of the patch as outside it and exits with 0: the workspace's apply stops Git's
    # discovery at the workspace. The check runs in the repository, which discovery must find.
    alone = {} if check_preimage else {"GIT_CEILING_DIRECTORIES": str(root.parent)}
    # Bytes, so that no platform's text stream rewrites the patch's line endings.
    data = patch.encode("utf-8")
    return run_git(root, *command, stdin=data, text=False, check=False, env=alone).returncode == 0


def _within(directory: Path, path: str) -> Path:
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts:
        msg = "prewrite patch path escapes root"
        raise ValueError(msg)
    return directory / relative


def _state(path: Path) -> tuple[object, ...] | None:
    """Return what the entry itself is, never what a link names; nothing where no entry is."""
    try:
        mode = path.lstat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        return None
    if stat.S_ISREG(mode):
        return "file", mode & 0o111, path.read_bytes()
    return "other", stat.S_IFMT(mode)


def _unread(
    changes: list[dict[str, object]],
    before: dict[str, tuple[object, ...] | None],
    after: dict[str, tuple[object, ...] | None],
) -> str:
    """Say why the workspace cannot be read as the patch's postimage, or nothing.

    Git skips by path and exits with 0, so every named path must show the patch. The one path
    that may hold what it held is one that a move in the same patch vacates and a creation
    fills. Postimages are read as the text of regular files, so a link or another kind of
    entry at a named path is not judged and is refused.
    """
    if any(state is not None and state[0] != "file" for state in after.values()):
        return "prewrite patch makes a named path no regular file"
    moved = (change for change in changes if change["old_path"] != change["path"])
    vacated = {str(change["old_path"]) for change in moved}
    same = {path for path, state in after.items() if state == before[path]}
    if same - vacated or len(same) == len(after):
        return "prewrite patch left a path that it names as it was"
    return ""


@contextmanager
def patched_workspace(
    root: Path, patch: str, changes: list[dict[str, object]]
) -> Generator[tuple[Path, dict[str, str | None]]]:
    """Yield a directory of the patched files, and each named path's text as the patch leaves it.

    Git's exit status alone does not prove the effect: a workspace that Git reads as part of
    another repository is left as it was. The workspace is read only when every named path
    shows the patch.
    """
    with tempfile.TemporaryDirectory(prefix="ethos-prewrite-postimage-") as temporary:
        workspace = Path(temporary)
        for change in changes:
            old_path = str(change["old_path"])
            if old_path == "/dev/null":
                continue
            source = _within(root, old_path)
            if not source.is_file():
                msg = "prewrite patch preimage missing"
                raise ValueError(msg)
            target = workspace / old_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        targets = {
            str(change["path"]): _within(workspace, str(change["path"])) for change in changes
        }
        before = {path: _state(target) for path, target in targets.items()}
        if not patch_applies(workspace, patch):
            msg = "prewrite patch postimage application failed"
            raise ValueError(msg)
        after = {path: _state(target) for path, target in targets.items()}
        if msg := _unread(changes, before, after):
            raise ValueError(msg)
        yield (
            workspace,
            {
                path: target.read_text(encoding="utf-8") if after[path] else None
                for path, target in targets.items()
            },
        )
