from __future__ import annotations

import os
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from ethos_kernel.action_graph import ActionNode


@dataclass(frozen=True)
class ActionRunResult:
    action_id: str
    command: tuple[str, ...]
    state: str
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""


class DryRunRunner:
    def run(self, node: ActionNode, *, root: Path) -> ActionRunResult:
        return ActionRunResult(
            action_id=node.id,
            command=node.command,
            state="planned",
            exit_code=None,
        )


class LocalSubprocessRunner:
    def run(self, node: ActionNode, *, root: Path) -> ActionRunResult:
        if _is_internal_ethos_json_command(node.command):
            return _run_internal_ethos_command(node, root=root)
        completed = subprocess.run(
            list(node.command),
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        return ActionRunResult(
            action_id=node.id,
            command=node.command,
            state="passed" if completed.returncode == 0 else "failed",
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def _is_internal_ethos_json_command(command: tuple[str, ...]) -> bool:
    return len(command) >= 4 and command[1:3] == ("-m", "ethos.cli") and "--json" in command


def _run_internal_ethos_command(node: ActionNode, *, root: Path) -> ActionRunResult:
    from ethos.cli import app

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
    return ActionRunResult(
        action_id=node.id,
        command=node.command,
        state="passed" if exit_code == 0 else "failed",
        exit_code=exit_code,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )
