from __future__ import annotations

import sys
from pathlib import Path

from ethos.adapters.gates import runner
from ethos_core.action_graph.core import ActionNode


def test_local_runner_executes_ethos_internal_json_gate_inprocess(monkeypatch) -> None:
    original_run = runner.subprocess.run

    def forbid_nested_ethos_cli(command: object, *_args: object, **_kwargs: object):
        if isinstance(command, list) and command[1:3] == ["-m", "ethos.cli"]:
            raise AssertionError("internal ETHOS JSON gates should not spawn a subprocess")
        return original_run(command, *_args, **_kwargs)

    monkeypatch.setattr(runner.subprocess, "run", forbid_nested_ethos_cli)
    node = ActionNode(
        id="status",
        kind="inspection",
        command=(sys.executable, "-m", "ethos.cli", "status", "--json"),
    )

    def inprocess_handler(
        action: ActionNode,
        _root: Path,
    ) -> runner.ActionRunResult | None:
        if action.command[1:3] != ("-m", "ethos.cli"):
            return None
        return runner.ActionRunResult(
            action_id=action.id,
            command=action.command,
            state="passed",
            exit_code=0,
            stdout='{"command": "status"}',
        )

    result = runner.LocalSubprocessRunner(inprocess_handler=inprocess_handler).run(
        node,
        root=Path.cwd(),
    )

    assert result.state == "passed"
    assert result.exit_code == 0
    assert '"command": "status"' in result.stdout
