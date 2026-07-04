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

from ethos.adapters.runner import ActionRunResult
from ethos.adapters.runner import classify_action_result
from ethos.surface.cli._base import app

if TYPE_CHECKING:
    from ethos_core.action_graph import ActionNode


def run_inprocess_cli_gate(node: ActionNode, root: Path) -> ActionRunResult | None:
    """Run an `ethos ... --json` action node in-process; None if not such a node."""
    if not (len(node.command) >= 4 and node.command[1:3] == ("-m", "ethos.cli")):
        return None
    if "--json" not in node.command:
        return None
    stdout = StringIO()
    stderr = StringIO()
    previous_cwd = Path.cwd()
    exit_code = 0
    try:
        os.chdir(root)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                app(list(node.command[3:]), exit_on_error=False)
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1
    except BaseException as exc:  # pragma: no cover - returned as runner failure.
        exit_code = 1
        stderr.write(f"{type(exc).__name__}: {exc}")
    finally:
        os.chdir(previous_cwd)
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
