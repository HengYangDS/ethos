"""The `ethos plan` request and its one operation."""

from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import operation
from ethos.contracts.operations.declaration import switch


class PlanRequest(CommandRequest):
    """Compile one TransitionPlan."""

    changed: bool = switch("Plan only the scope of the changed paths.")
    change: str | None = described(None, "Plan this active OpenSpec Change.")


PLAN = Command(
    name="plan",
    summary="Compile deterministic TransitionPlan.",
    request=PlanRequest,
    operations=(
        operation(
            "plan.compile",
            "Compile the TransitionPlan and the gates it requires.",
            select="",
            request="changed change",
            effects="read",
        ),
    ),
)
