"""Run one heavy local command once the host's queue admits it.

Every admitted run reports the command's exit status in `data.exit_status`, which the `process`
exit of `host run` exits with; a run the queue does not admit is a gap like any other.
"""

from pathlib import Path

from ethos.adapters.gates.host_admission import run_admitted
from ethos.contracts.operations.host import RunRequest
from ethos.repository.paradigm.parameters import seconds
from ethos.result import EthosResult


def run_host_command(root: Path, request: RunRequest) -> EthosResult:
    """Run the command when the host admits it, with its worker cap, and report its status."""
    gap, next_action = "host_run_command_missing", "ethos host run -- <command...>"
    if request.command:
        try:
            status = run_admitted(
                request.command, repository=root, seconds=seconds("admission", request.wait)
            )
        except ValueError as error:
            gap = str(error)
            next_action = "wait for the holder that the gap names, or declare more host slots"
        else:
            return EthosResult(
                command="host run",
                verdict="block" if status else "pass",
                state="completed",
                required_gaps=(f"host_command_failed:{status}",) if status else (),
                data={"exit_status": status},
            )
    return EthosResult(
        command="host run",
        verdict="block",
        state="gapped",
        required_gaps=(gap,),
        next_action=next_action,
    )
