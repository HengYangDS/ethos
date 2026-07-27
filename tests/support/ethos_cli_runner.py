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

from ethos.cli import app
from ethos.surface.cli.application import load_command_groups

if TYPE_CHECKING:
    from collections.abc import MutableMapping

ROOT = Path(__file__).resolve().parents[2]
PYTHONPATH = str(ROOT / "src")


class ImplicitApplyCheckoutError(AssertionError):
    """Raised when a test would mutate the repository checkout by default."""

    def __str__(self) -> str:
        return (
            "run_ethos* --apply calls must pass cwd=tmp_repo or --root tmp_repo; "
            "refusing to run a mutating command against the repository checkout"
        )


def _test_git_config_overlay_items(
    env: MutableMapping[str, str],
) -> tuple[tuple[str, str], ...]:
    """Return complete indexed Git configuration overlay entries from ``env``."""
    raw_count = env.get("GIT_CONFIG_COUNT", "0")
    try:
        count = int(raw_count)
    except ValueError:
        count = 0
    return tuple(
        (key, value)
        for index in range(count)
        if (key := env.get(f"GIT_CONFIG_KEY_{index}")) is not None
        and (value := env.get(f"GIT_CONFIG_VALUE_{index}")) is not None
    )


def _clear_test_git_config_overlay(env: MutableMapping[str, str]) -> None:
    """Remove every indexed Git configuration variable from ``env``."""
    raw_count = env.pop("GIT_CONFIG_COUNT", "0")
    try:
        count = int(raw_count)
    except ValueError:
        count = 0
    for index in range(count):
        env.pop(f"GIT_CONFIG_KEY_{index}", None)
        env.pop(f"GIT_CONFIG_VALUE_{index}", None)


def _write_test_git_config_overlay(
    env: MutableMapping[str, str], entries: tuple[tuple[str, str], ...]
) -> None:
    """Write one dense indexed Git configuration overlay into ``env``."""
    if not entries:
        return
    env["GIT_CONFIG_COUNT"] = str(len(entries))
    for index, (key, value) in enumerate(entries):
        env[f"GIT_CONFIG_KEY_{index}"] = key
        env[f"GIT_CONFIG_VALUE_{index}"] = value


def _without_test_git_config_overlay(env: MutableMapping[str, str]) -> dict[str, str]:
    """Remove test identity overlay but retain Git execution isolation."""
    clean = dict(env)
    retained = tuple(
        (key, value)
        for key, value in _test_git_config_overlay_items(env)
        if (key == "core.fsmonitor" and value == "false") or key == "safe.directory"
    )
    _clear_test_git_config_overlay(clean)
    _write_test_git_config_overlay(clean, retained)
    return clean


def _remove_test_git_config_overlay(env: MutableMapping[str, str]) -> dict[str, str]:
    """Remove identity overlays in-place but retain Git execution isolation."""
    original = dict(env)
    replacement = _without_test_git_config_overlay(env)
    _clear_test_git_config_overlay(env)
    _write_test_git_config_overlay(
        env,
        _test_git_config_overlay_items(replacement),
    )
    return original


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
    raise ImplicitApplyCheckoutError


def run_ethos_raw(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    _reject_implicit_apply_against_repository_checkout(args, cwd=cwd)
    if "--help" in args or "--version" in args:
        return _run_subprocess(*args, cwd=cwd)
    if "--json" not in args:
        return _run_subprocess(*args, cwd=cwd)
    return _run_inprocess(*args, cwd=cwd)


def _run_inprocess(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
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
    except BaseException as exc:
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
