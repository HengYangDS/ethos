"""Run one heavy local command once the host's queue admits it."""

from __future__ import annotations

from typing import Annotated

from cyclopts import App
from cyclopts import Parameter

import ethos.repository.paradigm.parameters as parameters
from ethos.adapters.gates.host_admission import run_admitted
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import resolve_root

_app = App(name="host", help="Admit heavy local work through the host's one queue.")
app.command(_app)


@_app.command
def run(
    *command: Annotated[str, Parameter(allow_leading_hyphen=True)],
    wait: Annotated[float | None, Parameter(name="--wait")] = None,
    json_output: JsonFlag = False,
) -> None:
    """Run COMMAND when the host admits it, with its worker cap, and exit with its status."""
    if not command:
        gap, next_action = "host_run_command_missing", "ethos host run -- <command...>"
    else:
        try:
            status = run_admitted(
                command,
                repository=resolve_root(None),
                seconds=parameters.seconds("admission", wait),
            )
        except ValueError as error:
            gap = str(error)
            next_action = "wait for the holder that the gap names, or declare more host slots"
        else:
            raise SystemExit(status)
    emit(
        EthosResult(
            command="host run",
            verdict="block",
            state="gapped",
            required_gaps=(gap,),
            next_action=next_action,
        ),
        json_output=json_output,
    )
