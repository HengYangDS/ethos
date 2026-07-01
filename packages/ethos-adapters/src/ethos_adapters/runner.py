from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ethos_core.action_graph import ActionNode


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


InProcessHandler = Callable[[ActionNode, Path], ActionRunResult | None]


class LocalSubprocessRunner:
    def __init__(self, *, inprocess_handler: InProcessHandler | None = None) -> None:
        self._inprocess_handler = inprocess_handler

    def run(self, node: ActionNode, *, root: Path) -> ActionRunResult:
        if self._inprocess_handler is not None:
            inprocess = self._inprocess_handler(node, root)
            if inprocess is not None:
                return inprocess
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
