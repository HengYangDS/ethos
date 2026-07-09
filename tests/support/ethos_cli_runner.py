from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import MutableMapping

ROOT = Path(__file__).resolve().parents[2]
PYTHONPATH = os.pathsep.join(
    str(ROOT / package / "src")
    for package in (
        "packages/ethos",
        "packages/ethos-core",
    )
)


def _test_git_config_overlay_keys(env: MutableMapping[str, str]) -> tuple[str, ...]:
    """Return pytest's indexed Git config overlay environment keys."""
    raw_count = env.get("GIT_CONFIG_COUNT", "0")
    try:
        count = int(raw_count)
    except ValueError:
        count = 0
    keys = ["GIT_CONFIG_COUNT"]
    for index in range(count):
        keys.extend((f"GIT_CONFIG_KEY_{index}", f"GIT_CONFIG_VALUE_{index}"))
    return tuple(keys)


def _without_test_git_config_overlay(env: MutableMapping[str, str]) -> dict[str, str]:
    """Copy ``env`` without pytest's environment-backed Git config overlay.

    The autouse git fixture disables commit signing through ``GIT_CONFIG_*`` so
    throwaway test repositories can commit without depending on a developer key.
    Product CLI checks must inspect repository truth, not that test-only overlay.
    Keep identity variables, but remove indexed Git config entries.
    """
    clean = dict(env)
    for key in _test_git_config_overlay_keys(env):
        clean.pop(key, None)
    return clean


def _remove_test_git_config_overlay(env: MutableMapping[str, str]) -> dict[str, str]:
    """Remove pytest's Git config overlay in-place and return removed values."""
    removed: dict[str, str] = {}
    for key in _test_git_config_overlay_keys(env):
        value = env.pop(key, None)
        if value is not None:
            removed[key] = value
    return removed


def run_ethos(*args: str, cwd: Path | None = None) -> dict[str, Any]:
    completed = run_ethos_raw(*args, cwd=cwd)
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return json.loads(completed.stdout)


def run_ethos_blocked(*args: str, cwd: Path | None = None) -> dict[str, Any]:
    """Run a command expected to BLOCK: assert non-zero exit, return JSON.

    Admission and transition commands enforce blocking verdicts via a non-zero
    process exit so git hooks, CI, MCP hosts, and shell chains can refuse unsafe
    operations from process status without reimplementing JSON parsing. This
    helper proves that contract.
    """
    completed = run_ethos_raw(*args, cwd=cwd)
    if completed.returncode == 0:
        msg = f"expected a blocked (non-zero exit) verdict, got exit 0: {completed.stdout}"
        raise AssertionError(msg)
    return json.loads(completed.stdout)


def _reject_implicit_apply_against_repository_checkout(
    args: tuple[str, ...], *, cwd: Path | None
) -> None:
    """Fail tests that would apply mutations to the real checkout by default.

    The helper's fallback cwd is the repository under test. Read-only contract
    tests may use that default, but mutating ``--apply`` calls must bind an
    explicit temporary repository via either ``cwd=...`` or ``--root ...``.
    """
    if "--apply" not in args or cwd is not None or "--root" in args:
        return
    raise AssertionError(
        "run_ethos* --apply calls must pass cwd=tmp_repo or --root tmp_repo; "
        "refusing to run a mutating command against the repository checkout"
    )


def run_ethos_raw(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    _reject_implicit_apply_against_repository_checkout(args, cwd=cwd)
    if "--help" in args or "--version" in args:
        return _run_subprocess(*args, cwd=cwd)
    if "--json" not in args:
        return _run_subprocess(*args, cwd=cwd)
    return _run_inprocess(*args, cwd=cwd)


def _run_inprocess(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    from ethos.cli import app
    from ethos.surface.cli._base import load_command_groups

    load_command_groups(list(args))
    previous_cwd = Path.cwd()
    removed_git_env: dict[str, str] = {}
    stdout = StringIO()
    stderr = StringIO()
    returncode = 0
    try:
        removed_git_env = _remove_test_git_config_overlay(os.environ)
        os.chdir(cwd or ROOT)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                app(list(args), exit_on_error=False)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
                returncode = code
    except BaseException as exc:  # pragma: no cover - exercised through failing tests.
        returncode = 1
        stderr.write(f"{type(exc).__name__}: {exc}")
    finally:
        os.chdir(previous_cwd)
        os.environ.update(removed_git_env)
    return subprocess.CompletedProcess(
        [sys.executable, "-m", "ethos.cli", *args],
        returncode,
        stdout.getvalue(),
        stderr.getvalue(),
    )


def _run_subprocess(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = _without_test_git_config_overlay(os.environ)
    env["PYTHONPATH"] = PYTHONPATH
    return subprocess.run(
        [sys.executable, "-m", "ethos.cli", *args],
        cwd=cwd or ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )


def write_role_policy(
    repo: Path,
    *,
    release_branch: str = "main",
    accepted_branch: str = "dev",
    candidate_branch: str = "stage/dev",
    work_branch_prefix: str = "lane/",
    submit_branch_prefix: str = "review/",
) -> None:
    """Write the branch-role policy fixture used by CLI contract tests."""
    workspace_path = repo / ".ethos" / "workspace.toml"
    workspace_path.write_text(
        "\n".join(
            [
                "[branch_roles]",
                f'release_branch = "{release_branch}"',
                f'accepted_branch = "{accepted_branch}"',
                f'candidate_branch = "{candidate_branch}"',
                f'work_branch_prefix = "{work_branch_prefix}"',
                f'submit_branch_prefix = "{submit_branch_prefix}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", workspace_path.as_posix()], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "configure branch roles",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
