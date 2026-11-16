"""Apply a prewrite patch to copies of its preimages, in a workspace that is its own repository."""

from __future__ import annotations

import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from collections.abc import Generator

# Git's summary of a patch names the mode of each entry that it creates, deletes or re-modes.
_SUMMARY_MODES = re.compile(rb"(?m)^ (?:create|delete) mode (\d+) |^ mode change (\d+) => (\d+)")
_REGULAR = {b"100644", b"100755"}


def _declares_other_kind(root: Path, patch: str) -> bool:
    """Ask Git which modes the patch declares; no reading of the patch's text stands in for it.

    A patch that Git cannot summarize declares none here; the apply in the workspace refuses it.
    """
    summary = run_git(
        root,
        "apply",
        "--summary",
        "--unsafe-paths",
        "-",
        stdin=patch.encode("utf-8"),
        text=False,
        check=False,
    )
    modes = {mode for found in _SUMMARY_MODES.findall(summary.stdout) for mode in found if mode}
    return not modes <= _REGULAR


def patch_applies(root: Path, patch: str, *, check_preimage: bool = False) -> bool:
    """Check the patch against the repository's files, or apply it in a workspace."""
    command = ["apply", "--whitespace=error-all", "-"]
    if check_preimage:
        command.insert(2, "--check")
    # Bytes, so that no platform's text stream rewrites the patch's line endings.
    completed = run_git(root, *command, stdin=patch.encode("utf-8"), text=False, check=False)
    return completed.returncode == 0


def _within(directory: Path, path: str) -> Path:
    """Return the named path under the directory; refuse one that leaves it or is Git's own."""
    parts = Path(path).parts
    if not parts or Path(path).is_absolute() or ".." in parts or parts[0].lower() == ".git":
        msg = "prewrite patch path escapes root"
        raise ValueError(msg)
    return directory / path


@contextmanager
def patched_workspace(
    root: Path, patch: str, changes: list[dict[str, object]]
) -> Generator[tuple[Path, dict[str, str | None]]]:
    """Yield a directory of the patched files, and each named path's text as the patch leaves it.

    The workspace is a repository of its own. A plain directory inside another repository's work
    tree is a part of that work tree to Git, which then skips every path of the patch as outside
    it and exits with 0, so the unchanged copies would be read as the postimage. In its own
    repository no path lies outside, and Git's exit status means what it means in a checkout.

    A patch that declares another kind of entry than a regular file is refused, and so is a
    preimage that is not a regular file: a postimage is read as the text of a regular file. A
    named path that the patch leaves without its file must be one that the patch deletes.
    """
    if _declares_other_kind(root, patch):
        msg = "prewrite patch makes a named path no regular file"
        raise ValueError(msg)
    with tempfile.TemporaryDirectory(prefix="ethos-prewrite-postimage-") as temporary:
        workspace = Path(temporary)
        targets = {
            str(change["path"]): (
                _within(workspace, str(change["path"])),
                bool(change.get("deleted")),
            )
            for change in changes
        }
        for change in changes:
            old_path = str(change["old_path"])
            if old_path == "/dev/null":
                continue
            source = _within(root, old_path)
            if source.is_symlink():
                msg = "prewrite patch preimage is no regular file"
                raise ValueError(msg)
            if not source.is_file():
                msg = "prewrite patch preimage missing"
                raise ValueError(msg)
            target = workspace / old_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        # No template: the workspace takes no hooks or configuration from the host's Git setup.
        founded = run_git(workspace, "init", "--quiet", "--template=", check=False).returncode == 0
        if not founded or not patch_applies(workspace, patch):
            msg = "prewrite patch postimage application failed"
            raise ValueError(msg)
        yield (
            workspace,
            {
                path: postimage_text(target, deleted=deleted)
                for path, (target, deleted) in targets.items()
            },
        )


def postimage_text(target: Path, *, deleted: bool) -> str | None:
    """Read a named path's text; only a deleted path may be left without its file."""
    if target.is_symlink():
        msg = "prewrite patch makes a named path no regular file"
        raise ValueError(msg)
    if target.is_file():
        return target.read_text(encoding="utf-8")
    if deleted:
        return None
    msg = "prewrite patch left a named path without its file"
    raise ValueError(msg)
