from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PRE_COMMIT_HOOK = ROOT / ".githooks" / "pre-commit"
STAGED_SECRET_RUNNER = ROOT / "tools" / "ci" / "scripts" / "run-staged-secrets-scan.sh"


def _write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _hook_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "hook-repo"
    repo.mkdir()
    _git(repo, "init", "-b", "work/test")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.test")

    staged_python = repo / "sample.py"
    staged_python.write_text("value = 1\n", encoding="utf-8")
    _git(repo, "add", "sample.py")
    _git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-m", "initial")

    hook = repo / ".githooks" / "pre-commit"
    hook.parent.mkdir()
    shutil.copy(PRE_COMMIT_HOOK, hook)
    hook.chmod(0o755)

    scripts = repo / "tools" / "ci" / "scripts"
    _write_executable(
        scripts / "run-staged-secrets-scan.sh",
        """#!/bin/sh
printf 'scan\\n' >> "${HOOK_LOG:?}"
exit "${STAGED_SCAN_EXIT:?}"
""",
    )
    _write_executable(
        scripts / "with-python-runtime.sh",
        """#!/bin/sh
case "$*" in
  *"ruff format"*)
    printf 'ruff\\n' >> "${HOOK_LOG:?}"
    ;;
  *"ethos.cli hook admit pre-tool"*)
    printf 'admission\\n' >> "${HOOK_LOG:?}"
    ;;
  *)
    printf 'unexpected_runtime_args:%s\\n' "$*" >&2
    exit 97
    ;;
esac
""",
    )

    staged_python.write_text("value = 2\n", encoding="utf-8")
    _git(repo, "add", "sample.py")
    return repo, hook, tmp_path / "hook-order.log"


def _run_hook(
    repo: Path,
    hook: Path,
    log: Path,
    *,
    scanner_exit: int,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    env = {
        **os.environ,
        "ETHOS_PYTHON": "/fake/python",
        "HOOK_LOG": str(log),
        "STAGED_SCAN_EXIT": str(scanner_exit),
    }
    completed = subprocess.run(
        [str(hook)],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return completed, lines


def _runner_fixture(
    tmp_path: Path,
    *,
    version: str | None,
    scan_exit: int,
) -> tuple[Path, dict[str, str], Path, Path]:
    repo = tmp_path / "runner-repo"
    repo.mkdir()
    (repo / ".gitleaks.toml").write_text("[extend]\nuseDefault = true\n", encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    bash = shutil.which("bash")
    assert bash is not None
    (fake_bin / "bash").symlink_to(bash)

    args_log = tmp_path / "gitleaks-args.log"
    calls_log = tmp_path / "gitleaks-calls.log"
    if version is not None:
        _write_executable(
            fake_bin / "gitleaks",
            """#!/bin/sh
if [ "${1:-}" = "version" ]; then
  printf '%s\\n' "${FAKE_GITLEAKS_VERSION:?}"
  exit 0
fi
printf '%s\\n' "$@" > "${FAKE_GITLEAKS_ARGS:?}"
printf 'scan\\n' >> "${FAKE_GITLEAKS_CALLS:?}"
exit "${FAKE_GITLEAKS_SCAN_EXIT:?}"
""",
        )

    env = {
        **os.environ,
        "PATH": str(fake_bin),
        "FAKE_GITLEAKS_VERSION": version or "",
        "FAKE_GITLEAKS_SCAN_EXIT": str(scan_exit),
        "FAKE_GITLEAKS_ARGS": str(args_log),
        "FAKE_GITLEAKS_CALLS": str(calls_log),
    }
    return repo, env, args_log, calls_log


def _run_staged_secret_runner(
    repo: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    assert STAGED_SECRET_RUNNER.is_file(), f"missing runner: {STAGED_SECRET_RUNNER}"
    assert os.access(STAGED_SECRET_RUNNER, os.X_OK), "staged runner must be executable"
    return subprocess.run(
        [str(STAGED_SECRET_RUNNER), str(repo)],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _expected_staged_args(repo: Path) -> list[str]:
    return [
        "git",
        "--staged",
        "--config",
        str(repo / ".gitleaks.toml"),
        "--redact=100",
        "--no-banner",
        str(repo),
    ]


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


def test_pre_commit_places_staged_secret_scan_before_ruff_and_admission() -> None:
    script = PRE_COMMIT_HOOK.read_text(encoding="utf-8")
    empty_index_guard = 'if [ "${#staged[@]}" -eq 0 ]; then\n  exit 0\nfi'
    scanner = '"${repo_root}/tools/ci/scripts/run-staged-secrets-scan.sh" "${repo_root}"'
    staged_python = "staged_python=()"
    ruff = '"${runtime_runner}" -- uv run --group dev ruff format'
    admission = '"${runtime_runner}" -- "${runtime_python}" -m ethos.cli hook admit pre-tool'

    assert script.index(empty_index_guard) < script.index(scanner)
    assert script.index(scanner) < script.index(staged_python)
    assert script.index(staged_python) < script.index(ruff)
    assert script.index(ruff) < script.index(admission)
    for forbidden in (
        "gitleaks protect",
        "install-gitleaks.sh",
        "credential-governance",
    ):
        assert forbidden not in script


def test_pre_commit_staged_secret_failure_blocks_ruff_and_admission(
    tmp_path: Path,
) -> None:
    repo, hook, log = _hook_fixture(tmp_path)

    completed, calls = _run_hook(repo, hook, log, scanner_exit=7)

    assert completed.returncode == 7
    assert calls == ["scan"]


def test_pre_commit_clean_scan_runs_scan_then_ruff_then_admission(
    tmp_path: Path,
) -> None:
    repo, hook, log = _hook_fixture(tmp_path)

    completed, calls = _run_hook(repo, hook, log, scanner_exit=0)

    assert completed.returncode == 0, completed.stderr
    assert calls == ["scan", "ruff", "admission"]


def test_staged_secret_runner_fails_closed_when_gitleaks_is_missing(
    tmp_path: Path,
) -> None:
    repo, env, args_log, calls_log = _runner_fixture(
        tmp_path,
        version=None,
        scan_exit=0,
    )

    completed = _run_staged_secret_runner(repo, env)

    assert completed.returncode == 1
    assert completed.stderr.strip() == "staged_secret_gitleaks_missing:expected=8.30.1"
    assert args_log.exists() is False
    assert calls_log.exists() is False


def test_staged_secret_runner_rejects_version_mismatch_before_scan(
    tmp_path: Path,
) -> None:
    repo, env, args_log, calls_log = _runner_fixture(
        tmp_path,
        version="9.0.0",
        scan_exit=0,
    )

    completed = _run_staged_secret_runner(repo, env)

    assert completed.returncode == 1
    assert completed.stderr.strip() == (
        "staged_secret_gitleaks_version_mismatch:expected=8.30.1:actual=9.0.0"
    )
    assert args_log.exists() is False
    assert calls_log.exists() is False


def test_staged_secret_runner_uses_exact_args_and_propagates_findings(
    tmp_path: Path,
) -> None:
    repo, env, args_log, calls_log = _runner_fixture(
        tmp_path,
        version="8.30.1",
        scan_exit=7,
    )

    completed = _run_staged_secret_runner(repo, env)

    assert completed.returncode == 7
    assert args_log.read_text(encoding="utf-8").splitlines() == _expected_staged_args(repo)
    assert calls_log.read_text(encoding="utf-8").splitlines() == ["scan"]


def test_staged_secret_runner_returns_zero_for_clean_index(tmp_path: Path) -> None:
    repo, env, args_log, calls_log = _runner_fixture(
        tmp_path,
        version="8.30.1",
        scan_exit=0,
    )

    completed = _run_staged_secret_runner(repo, env)

    assert completed.returncode == 0, completed.stderr
    assert args_log.read_text(encoding="utf-8").splitlines() == _expected_staged_args(repo)
    assert calls_log.read_text(encoding="utf-8").splitlines() == ["scan"]
