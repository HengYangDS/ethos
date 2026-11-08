"""Select one root catalog operation for a request, the same way for every transport.

`select_operation` validates a request against its command's model and selects the one operation
its set fields choose, or returns the refusal every transport reports. The six root operations
select through `catalog_operation` before they run, so the CLI, the SDK and MCP refuse the same
requests alike and a refused request runs nothing.
"""

import inspect
from collections.abc import Callable
from collections.abc import Mapping
from dataclasses import dataclass
from functools import wraps
from importlib import import_module
from pathlib import Path

from pydantic import ValidationError

from ethos.application.invocation import application_result
from ethos.contracts.operations import COMMANDS
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import Operation
from ethos.result import EthosResult

# The application operation of each root command, which selects before it runs.
OPERATIONS = {
    "status": "ethos.application.inspection:inspect_repository",
    "plan": "ethos.application.plan:plan_repository",
    "prove": "ethos.application.proof.operation:prove_repository",
    "land": "ethos.application.land.operation:land_repository",
    "publish": "ethos.application.publication.operation:publish_repository",
    "adopt": "ethos.application.adoption:adopt_repository",
}


@dataclass(frozen=True, slots=True)
class Selected:
    """The operation a request selects, with the validated request it runs."""

    operation: Operation
    request: CommandRequest


@dataclass(frozen=True, slots=True)
class Refused:
    """The result of a request that selects no operation; nothing ran."""

    result: EthosResult


def usage_refusal(
    command: str, gaps: tuple[str, ...], data: Mapping[str, object], *, message: str = ""
) -> EthosResult:
    """Return the result of a request that names no operation or misuses its command."""
    help_argv = "ethos --help" if command == "ethos" else f"ethos {command} --help"
    return EthosResult(
        command=command,
        verdict="block",
        state="usage_refused",
        required_gaps=gaps,
        diagnostics=(
            ({"severity": "error", "code": gaps[0].partition(":")[0], "message": message},)
            if message
            else ()
        ),
        next_action=f"Choose one operation and its fields from `{help_argv}`.",
        data=dict(data),
    )


def select_operation(
    command: str, fields: Mapping[str, object] | CommandRequest
) -> Selected | Refused:
    """Select the operation a request's set fields choose, or return the refusal of the request."""
    declared = COMMANDS[command]
    if isinstance(fields, declared.request):
        request = fields
    else:
        try:
            request = declared.request.model_validate(dict(fields))
        except ValidationError as error:
            usage = [f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in error.errors()]
            return Refused(
                usage_refusal(command, (f"command_usage_invalid:{command}",), {"usage": usage})
            )
    selection = declared.select(declared.present(request))
    if selection.operation is None:
        return Refused(usage_refusal(command, selection.gaps, {"selection": selection.detail}))
    return Selected(selection.operation, request)


def catalog_operation[**P](
    command: str,
) -> Callable[[Callable[P, EthosResult]], Callable[P, EthosResult]]:
    """Run a root operation only for a request that selects one of its catalog operations."""

    def decorate(function: Callable[P, EthosResult]) -> Callable[P, EthosResult]:
        signature = inspect.signature(function)
        normalized = application_result(command)(function)

        @wraps(function)
        def selected(*args: P.args, **kwargs: P.kwargs) -> EthosResult:
            arguments = signature.bind(*args, **kwargs).arguments
            # `prove` takes its request whole; the other root operations take its fields.
            fields = arguments.get(
                "request", {name: value for name, value in arguments.items() if name != "root"}
            )
            chosen = select_operation(command, fields)
            if isinstance(chosen, Refused):
                return chosen.result
            return normalized(*args, **kwargs)

        return selected

    return decorate


def invoke(command: str, root: Path, request: CommandRequest) -> EthosResult:
    """Run one validated request through its root command's application operation."""
    module, _separator, name = OPERATIONS[command].partition(":")
    function = getattr(import_module(module), name)
    if "request" in inspect.signature(function).parameters:
        return function(root, request=request)
    return function(root, **dict(request))
