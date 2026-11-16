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

# A patch declares each entry's kind by its mode; a regular file is one of these two.
_OTHER_KIND = re.compile(r"(?m)^(?:new file mode|new mode) (?!100644$|100755$)")


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
    relative = Path(path)
    if relative.is_absolute() or ".." in relative.parts or relative.parts[0].lower() == ".git":
        msg = "prewrite patch path escapes root"
        raise ValueError(msg)
    return directory / relative


@contextmanager
def patched_workspace(
    root: Path, patch: str, changes: list[dict[str, object]]
) -> Generator[tuple[Path, dict[str, str | None]]]:
    """Yield a directory of the patched files, and each named path's text as the patch leaves it.

    The workspace is a repository of its own. A plain directory inside another repository's work
    tree is a part of that work tree to Git, which then skips every path of the patch as outside
    it and exits with 0, so the unchanged copies would be read as the postimage. In its own
    repository no path lies outside, and Git's exit status means what it means in a checkout.

    A patch that declares another kind of entry than a regular file is refused: a postimage is
    read as the text of a regular file, and a link would be admitted without what it names.
    """
    if _OTHER_KIND.search(patch):
        msg = "prewrite patch makes a named path no regular file"
        raise ValueError(msg)
    with tempfile.TemporaryDirectory(prefix="ethos-prewrite-postimage-") as temporary:
        workspace = Path(temporary)
        targets = {
            str(change["path"]): _within(workspace, str(change["path"])) for change in changes
        }
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
        founded = run_git(workspace, "init", "--quiet", check=False).returncode == 0
        if not founded or not patch_applies(workspace, patch):
            msg = "prewrite patch postimage application failed"
            raise ValueError(msg)
        yield (
            workspace,
            {
                path: target.read_text(encoding="utf-8") if target.is_file() else None
                for path, target in targets.items()
            },
        )
