"""The `ethos host run` request and its one operation."""

from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import operation


class RunRequest(CommandRequest):
    """Run one heavy local command once the host's queue admits it."""

    command: tuple[str, ...] = described((), "The command to run, after `--`.")
    wait: float | None = described(None, "Seconds to wait for admission.")


HOST_RUN = Command(
    name="host run",
    summary="Run COMMAND when the host admits it, with its worker cap, and exit with its status.",
    request=RunRequest,
    positionals=("command",),
    hyphen=("command",),
    operations=(
        operation(
            "host.run",
            "Run the command once the host admits it, then exit with the command's status.",
            select="",
            request="command wait",
            effects="execute opaque",
            authorization="human",
            destructive=True,
            exit_kind="process",
        ),
    ),
)
