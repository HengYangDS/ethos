"""Run public CLI tests with explicit repository and mutation isolation."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from contextlib import chdir
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast
from typing import override
from unittest.mock import patch

from cyclopts.exceptions import CycloptsError

from ethos.adapters.repo.invocation_facts import invocation_scope
from ethos.application.catalog import Selected
from ethos.application.catalog import select_operation
from ethos.contracts.operations.catalog import select_argv
from ethos.result import expand_result
from ethos.surface.cli.application import app
from ethos.surface.cli.application import load_command_groups
from ethos.surface.cli.application import run_application
from tests.support.git_isolation import GIT_ISOLATION

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from ethos.adapters.repo.hook.observation import CommitPolicyEnforcement

ROOT = Path(__file__).resolve().parents[2]
PYTHONPATH = str(ROOT / "src")


class ImplicitApplyCheckoutError(AssertionError):
    """Raised when a test would mutate the repository checkout by default."""

    @override
    def __str__(self) -> str:
        return (
            "run_ethos* --apply calls must pass cwd=tmp_repo or --root tmp_repo; "
            "refusing to run a mutating command against the repository checkout"
        )


def _test_git_config_overlay_items(env: MutableMapping[str, str]) -> tuple[tuple[str, str], ...]:
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


def _without_test_git_config_overlay(env: MutableMapping[str, str]) -> dict[str, str]:
    """Remove test identity overlay but retain Git execution isolation."""
    clean = {
        key: value
        for key, value in env.items()
        if key != "GIT_CONFIG_COUNT"
        and not key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))
    }
    retained = tuple(
        (key, value)
        for key, value in _test_git_config_overlay_items(env)
        if (key, value) in GIT_ISOLATION or key == "safe.directory"
    )
    if retained:
        clean["GIT_CONFIG_COUNT"] = str(len(retained))
        for index, (key, value) in enumerate(retained):
            clean[f"GIT_CONFIG_KEY_{index}"] = key
            clean[f"GIT_CONFIG_VALUE_{index}"] = value
    return clean


def run_ethos(*args: str, cwd: Path | None = None, full_payload: bool = True) -> dict[str, Any]:
    """Return the full result; `full_payload=False` returns the bounded payload an agent sees."""
    completed = run_ethos_raw(*args, cwd=cwd)
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    payload = json.loads(completed.stdout)
    return expand_result(payload) if full_payload else payload


def commit_policy_capability(repo: Path) -> tuple[dict[str, Any], CommitPolicyEnforcement]:
    """Return public status and the commit-policy enforcement it projects for one repository."""
    projected = run_ethos("status", "--root", repo.as_posix(), "--json", cwd=repo)
    return projected, cast(
        "CommitPolicyEnforcement", projected["data"]["commit_policy_enforcement"]
    )


def _externalized(payload: object) -> bool:
    """Every command's result is bounded; tests that read detail read the bound artifact."""
    return isinstance(payload, dict) and isinstance(payload.get("bound"), dict)


def full_result(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    """Parse one CLI run's JSON result, reading the full result a bounded payload references."""
    return expand_result(json.loads(completed.stdout))


def result_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a result's data, read from the artifact that an oversized result points at."""
    return expand_result(payload)["data"]


def run_ethos_blocked(
    *args: str, cwd: Path | None = None, full_payload: bool = True
) -> dict[str, Any]:
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
    payload = json.loads(completed.stdout)
    return expand_result(payload) if full_payload else payload


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
        return run_ethos_process(*args, cwd=cwd)
    if "--json" not in args:
        return run_ethos_process(*args, cwd=cwd)
    return _run_inprocess(*args, cwd=cwd)


def _run_inprocess(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    load_command_groups(list(args))
    stdout, stderr, returncode = StringIO(), StringIO(), 0
    with (
        chdir(cwd or ROOT),
        patch.dict(os.environ, _without_test_git_config_overlay(os.environ), clear=True),
        redirect_stdout(stdout),
        redirect_stderr(stderr),
        invocation_scope(),
    ):
        try:
            run_application(list(args))
        except SystemExit as exc:
            returncode = exc.code if isinstance(exc.code, int) else 1
    _require_live_next(stdout.getvalue())
    return subprocess.CompletedProcess(
        [sys.executable, "-m", "ethos.cli", *args], returncode, stdout.getvalue(), stderr.getvalue()
    )


def _require_live_next(stdout: str) -> None:
    """Every structured next step is an invocation the live CLI parses, never misread prose.

    A root step names the catalog operation that the parsed request selects.
    """
    try:
        payload = json.loads(stdout)
    except ValueError:
        return
    step = payload.get("next") if isinstance(payload, dict) else None
    # A decision carries the argv a person approves, so it must parse as well.
    if not isinstance(step, dict) or step.get("kind") not in {"command", "decision"}:
        return
    if not step["argv"]:
        return
    tokens = list(step["argv"][1:])
    load_command_groups(tokens)
    try:
        bound = app.parse_args(tokens, exit_on_error=False, print_error=False)[1]
    except CycloptsError as error:
        message = f"next_argv_not_parsed:{shlex.join(step['argv'])}"
        raise AssertionError(message) from error
    root = select_argv(step["argv"])
    if root is None:
        return
    bound.apply_defaults()
    chosen = select_operation(root[0].name, bound.arguments["request"])
    form = chosen.operation.id if isinstance(chosen, Selected) else ""
    if not form or step["form"] != form:
        message = f"next_form_not_selected:{shlex.join(step['argv'])}:{step['form']}:{form}"
        raise AssertionError(message)


def run_ethos_process(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the console path in a fresh process, whatever the arguments."""
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
