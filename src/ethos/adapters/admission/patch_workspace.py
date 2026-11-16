"""Apply a prewrite patch to copies of its preimages, in a workspace that is its own repository."""

from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from collections.abc import Generator

# The modes of a regular file, and the mode that Git gives a path that is gone.
_REGULAR = {"000000", "100644", "100755"}
_EFFECTS = {"A": "create", "D": "delete"}


def patch_applies(root: Path, patch: str, *, check_preimage: bool = False) -> bool:
    """Check the patch against the repository's files, or apply it there."""
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


def _observed(workspace: Path, patch: str, staged: list[str]) -> dict[str, tuple[str, str]]:
    """Apply the patch with the workspace's own index; return each changed path's status and mode.

    Git compares the index before and after the apply, without rename detection, and names
    every path that the patch changed with its new mode. Nothing here reads the patch's text.
    """

    def git(*arguments: str, stdin: bytes | None = None) -> bytes:
        done = run_git(workspace, *arguments, stdin=stdin, text=False, check=False)
        if done.returncode:
            msg = "prewrite patch postimage application failed"
            raise ValueError(msg)
        return done.stdout

    # No template: the workspace takes no hooks or configuration from the host's Git setup.
    git("init", "--quiet", "--template=")
    names = "".join(f"{path}\0" for path in staged).encode("utf-8")
    git("update-index", "--add", "-z", "--stdin", stdin=names)
    before = git("write-tree").decode().strip()
    git("apply", "--index", "--whitespace=error-all", "-", stdin=patch.encode("utf-8"))
    after = git("write-tree").decode().strip()
    fields = git("diff-tree", "-r", "-z", "--raw", "--no-renames", before, after).split(b"\0")
    return {
        path.decode("utf-8"): (entry.split()[4].decode(), entry.split()[1].decode())
        for entry, path in zip(fields[::2], fields[1::2], strict=False)
    }


@contextmanager
def patched_workspace(
    root: Path, patch: str, changes: list[dict[str, object]]
) -> Generator[tuple[Path, dict[str, str | None], dict[str, str]]]:
    """Yield a directory of the patched files, each changed path's text, and its effect.

    The workspace is a repository of its own. A plain directory inside another repository's work
    tree is a part of that work tree to Git, which then skips every path of the patch as outside
    it and exits with 0, so the unchanged copies would be read as the postimage. In its own
    repository no path lies outside, and Git's exit status means what it means in a checkout.

    What the patch does is observed there and not read from its text: the workspace's index
    names each path that Git changed, whether Git created or deleted it, and its mode. A path
    that is no regular file afterwards is refused, and so is a preimage that is none: a
    postimage is read as the text of a regular file. A named path without its file must be one
    that Git deleted, and a path that Git deleted is read as deleted where no change names it,
    which is the source of a move.
    """
    with tempfile.TemporaryDirectory(prefix="ethos-prewrite-postimage-") as temporary:
        workspace = Path(temporary)
        named = {str(change["path"]) for change in changes}
        for path in named:
            _within(workspace, path)
        staged: list[str] = []
        for old_path in dict.fromkeys(str(change["old_path"]) for change in changes):
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
            staged.append(old_path)
        observed = _observed(workspace, patch, staged)
        if not all(mode in _REGULAR for _status, mode in observed.values()):
            msg = "prewrite patch makes a named path no regular file"
            raise ValueError(msg)
        # A path that Git deleted is read as deleted where no change names it: a move's source.
        removed = {path for path, (status, _mode) in observed.items() if status == "D"}
        effects = {
            path: _EFFECTS.get(observed.get(path, ("M", ""))[0], "modify")
            for path in sorted(named | removed)
        }
        yield (
            workspace,
            {path: _postimage(workspace / path, effect) for path, effect in effects.items()},
            effects,
        )


def _postimage(target: Path, effect: str) -> str | None:
    """Read a changed path's text; only a path that Git deleted may be without its file."""
    if effect == "delete":
        return None
    if not target.is_file():
        msg = "prewrite patch left a named path without its file"
        raise ValueError(msg)
    return target.read_text(encoding="utf-8")
