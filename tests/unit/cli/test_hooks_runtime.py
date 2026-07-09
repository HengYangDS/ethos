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
        '--remote-head "$remote_sha"',
        '"$ethos_python" -m ethos.cli hook admit pre-tool',
    ):
        assert expected in scripts


def test_pre_commit_blocks_staged_python_format_drift() -> None:
    script = Path(".githooks/pre-commit").read_text(encoding="utf-8")

    assert "git diff --cached --name-only --diff-filter=ACMR -- '*.py'" in script
    assert "ruff format --check" in script
    assert "pre_commit_python_format_failed" in script
