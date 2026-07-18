from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def test_git_hooks_use_repo_bound_python_runtime() -> None:
    scripts = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            ".githooks/pre-commit",
            ".githooks/pre-push",
            ".githooks/reference-transaction",
        )
    )

    for expected in (
        'repo_root="$(git rev-parse --show-toplevel)"',
        "tools/ci/scripts/with-python-runtime.sh",
        "packages/ethos/src:$repo_root/packages/ethos-core/src",
        'runtime_python="${ETHOS_PYTHON:-${PYTHON:-${repo_root}/build/runtime/venv/bin/python}}"',
        '"${runtime_runner}" -- "${runtime_python}" -m ethos.cli hook pre-push',
        '"${runtime_runner}" -- "${runtime_python}" -m ethos.cli hook ref-transaction',
        '--remote-head "$remote_sha"',
        '"${runtime_runner}" -- "${runtime_python}" -m ethos.cli hook admit pre-tool',
    ):
        assert expected in scripts
    assert ".venv/bin/python" not in scripts
    assert "uv run --package ethos python -m ethos.cli hook" not in scripts


def test_pre_commit_blocks_staged_python_format_drift() -> None:
    script = Path(".githooks/pre-commit").read_text(encoding="utf-8")

    assert "git diff --cached --name-only --diff-filter=ACMR -- '*.py'" in script
    assert 'ruff_config_path=".config/checks/ruff/ruff.toml"' in script
    assert "build/runtime/tool-cache/ruff" in script
    assert "--cache-dir" in script
    assert (
        'ruff format --cache-dir "${ruff_cache_dir}" --config "${ruff_config_path}" --check'
        in script
    )
    assert '"${runtime_runner}" -- uv run --group dev ruff format' in script
    assert "pre_commit_python_format_failed" in script


def test_reference_transaction_updates_work_lane_lease_after_commit() -> None:
    script = Path(".githooks/reference-transaction").read_text(encoding="utf-8")

    assert 'phase="$1"' in script
    assert '--phase "$phase"' in script
    assert '"state":"lease_head_advanced"' in script
    assert "lease repair required" in script


def test_reference_transaction_skips_runtime_bootstrap_for_fresh_work_lane_ref(
    tmp_path: Path,
) -> None:
    """A no-op Work Lane setup ref must not bootstrap a runtime before its lease exists."""
    source_root = Path.cwd()
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "dev"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.test"], cwd=repo, check=True)
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True)
    subprocess.run(["git", "branch", "candidate/dev"], cwd=repo, check=True)

    hooks = repo / ".githooks"
    hooks.mkdir()
    hook = hooks / "reference-transaction"
    runtime = repo / "tools" / "ci" / "scripts" / "with-python-runtime.sh"
    runtime.parent.mkdir(parents=True)
    shutil.copy(source_root / ".githooks" / "reference-transaction", hook)
    shutil.copy(source_root / "tools" / "ci" / "scripts" / "with-python-runtime.sh", runtime)
    hook.chmod(0o755)
    runtime.chmod(0o755)
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo, check=True)
    subprocess.run(["git", "config", "ethos.acceptedBranch", "dev"], cwd=repo, check=True)

    marker = tmp_path / "uv-invoked"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uv = fake_bin / "uv"
    fake_uv.write_text(f'#!/bin/sh\ntouch "{marker}"\nexit 0\n', encoding="utf-8")
    fake_uv.chmod(0o755)
    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}

    created = subprocess.run(
        [
            "git",
            "worktree",
            "add",
            "-b",
            "work/fresh",
            str(tmp_path / "fresh"),
            "candidate/dev",
        ],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert created.returncode == 0, created.stderr
    assert marker.exists() is False
