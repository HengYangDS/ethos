from __future__ import annotations

import subprocess
from dataclasses import dataclass
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
