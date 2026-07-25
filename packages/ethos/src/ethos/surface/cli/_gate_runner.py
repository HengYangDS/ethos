"""In-process CLI gate runner — execute an `ethos ... --json` gate without a subprocess.

Prove and the lane commands run governance gates that are themselves ETHOS CLI
invocations. Running them in-process (redirecting stdout/stderr, catching SystemExit)
avoids a subprocess per gate while still classifying the result through the normal
runner. Lives at the surface because it drives the CLI `app` object.
"""

from __future__ import annotations

import os
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.gates.runner import ActionRunResult
from ethos.adapters.gates.runner import classify_action_result
from ethos.surface.cli._base import app
from ethos.surface.cli._base import load_command_groups

if TYPE_CHECKING:
    from ethos_core.contracts.plan import PlanNode


def _current_cwd() -> Path | None:
    """Return the current directory, or None when the host removed it."""
    try:
        return Path.cwd()
    except OSError:
        return None


def _restore_cwd(previous_cwd: Path | None, root: Path) -> None:
    """Restore process cwd without raising when a worktree disappeared."""
    for candidate in (previous_cwd, root, Path("/")):
        if candidate is None:
            continue
        try:
            os.chdir(candidate)
        except OSError:
            continue
        else:
            return


def run_inprocess_cli_gate(node: PlanNode, root: Path) -> ActionRunResult | None:
    """Run an `ethos ... --json` PlanIR node in-process; None if not such a node."""
    if "--json" not in node.command:
        return None
    if len(node.command) >= 4 and node.command[1:3] == ("-m", "ethos.cli"):
        command_args = list(node.command[3:])
    elif len(node.command) >= 2 and node.command[0] == "ethos":
        command_args = list(node.command[1:])
    else:
        return None
    stdout = StringIO()
    stderr = StringIO()
    previous_cwd = _current_cwd()
    cwd_unavailable = previous_cwd is None
    if cwd_unavailable:
        stderr.write("FileNotFoundError: current working directory is unavailable")
    exit_code = 0
    try:
        os.chdir(root)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                load_command_groups(command_args)
                app(command_args, exit_on_error=False)
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1
    except BaseException as exc:  # pragma: no cover - returned as runner failure.
        exit_code = 1
        stderr.write(f"{type(exc).__name__}: {exc}")
    finally:
        _restore_cwd(previous_cwd, root)
    if cwd_unavailable:
        exit_code = 1
    state, diagnostics = classify_action_result(
        exit_code=exit_code,
        stdout=stdout.getvalue(),
    )
    return ActionRunResult(
        action_id=node.id,
        command=node.command,
        state=state,
        exit_code=exit_code,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
        diagnostics=diagnostics,
    )
