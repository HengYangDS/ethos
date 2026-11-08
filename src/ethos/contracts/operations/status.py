"""The `ethos status` request and its one operation."""

from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import operation


class StatusRequest(CommandRequest):
    """Observe one repository."""

    change: str | None = described(None, "Observe this active OpenSpec Change.")


COMMAND = Command(
    name="status",
    summary="Inspect bounded truth, authority, gaps, coordination, and next action.",
    request=StatusRequest,
    operations=(
        operation(
            "status.inspect",
            "Inspect repository facts, authority, gaps, coordination and the next action.",
            select="",
            request="change",
            effects="read",
        ),
    ),
)
