from __future__ import annotations

from pathlib import Path


def test_git_hooks_use_repo_bound_python_runtime() -> None:
    scripts = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (".githooks/pre-commit", ".githooks/pre-push")
    )

    for expected in (
        'repo_root="$(git rev-parse --show-toplevel)"',
        '"$repo_root/.venv/bin/python"',
        "packages/ethos/src:$repo_root/packages/ethos-core/src",
        '"$ethos_python" -m ethos.cli hook pre-push',
        '"$ethos_python" -m ethos.cli hook admit pre-tool',
    ):
        assert expected in scripts
