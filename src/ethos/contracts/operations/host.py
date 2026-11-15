"""The `ethos host` commands: one run the queue admits, and one read of the queue."""

from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import operation


class RunRequest(CommandRequest):
    """Run one heavy local command once the host's queue admits it."""

    command: tuple[str, ...] = described((), "The command to run, after `--`.")
    wait: float | None = described(None, "Seconds to wait for admission, in total.")
    work: str | None = described(None, "The directory of build/runtime/work that this run owns.")


class StatusRequest(CommandRequest):
    """Read this host's declaration and queue."""

    guest_cpus: int | None = described(
        None, "The guests' virtual CPU count to check against the reservation."
    )


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
            request="command wait work",
            effects="execute opaque",
            authorization="human",
            destructive=True,
            exit_kind="process",
        ),
    ),
)

HOST_STATUS = Command(
    name="host status",
    summary="List this host's declaration, its load and every live ticket in arrival order.",
    request=StatusRequest,
    operations=(
        operation(
            "host.status",
            "Read the declaration and the queue, and check the guests' CPUs against it.",
            select="",
            request="guest_cpus",
            effects="read",
        ),
    ),
)

HOST = (HOST_RUN, HOST_STATUS)
