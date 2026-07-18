from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def test_test_git_init_does_not_inherit_global_template_hooks(tmp_path: Path) -> None:
    """Temporary Git repositories must not inherit developer-global hooks."""
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "-C", repo.as_posix(), "init", "-q"], check=True)

    assert not (repo / ".git" / "hooks" / "pre-commit").exists()
