"""Select one root catalog operation for a request, and run the one implementation it maps to.

`select_operation` validates a request against its command's model and selects the one operation
its set fields choose, or returns the refusal every transport reports. `invoke` runs the selected
operation's implementation, the function `IMPLEMENTATIONS` names for it, so the CLI, the SDK and
MCP run one body for one request and a refused request runs nothing. Only `invoke` calls an
implementation: one imported directly skips the selection and the failure normalization.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

from pydantic import ValidationError

from ethos.application.invocation import application_result
from ethos.contracts.operations.catalog import COMMANDS
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import Operation
from ethos.result import EthosResult

_LAND = "ethos.application.land.operation"
_PUBLISH = "ethos.application.publication.operation"
_PROVE = "ethos.application.proof.operation"
_ADOPT = "ethos.application.adoption"
# Each operation's implementation, `(root, request) -> EthosResult`; operations that share a body
# share its function, which reads only the fields of its own operations.
IMPLEMENTATIONS = {
    "status.inspect": "ethos.application.inspection:inspect_status",
    "plan.compile": "ethos.application.plan:compile_transition_plan",
    "proof.preview": f"{_PROVE}:prove_governed",
    "proof.execute": f"{_PROVE}:prove_governed",
    "proof.run": f"{_PROVE}:prove_governed",
    "proof.readiness": f"{_PROVE}:prove_readiness",
    "proof.host": f"{_PROVE}:prove_on_host",
    "land.preview": f"{_LAND}:land_on_candidate",
    "land.apply": f"{_LAND}:land_on_candidate",
    "land.closeout.preview": f"{_LAND}:close_out",
    "land.closeout.apply": f"{_LAND}:close_out",
    "land.release.preview": f"{_LAND}:release_accepted_head",
    "land.release.apply": f"{_LAND}:release_accepted_head",
    "land.retag.preview": f"{_LAND}:move_release_tags",
    "land.retag.apply": f"{_LAND}:move_release_tags",
    "publish.readiness": f"{_PUBLISH}:report_readiness",
    "publish.probe": f"{_PUBLISH}:project_publication",
    "publish.apply": f"{_PUBLISH}:project_publication",
    "publish.retire.probe": f"{_PUBLISH}:project_publication",
    "publish.retire.apply": f"{_PUBLISH}:project_publication",
    "adopt.preview": f"{_ADOPT}:adopt_existing",
    "adopt.apply": f"{_ADOPT}:adopt_existing",
    "adopt.runtime.preview": f"{_ADOPT}:adopt_existing",
    "adopt.runtime.apply": f"{_ADOPT}:adopt_existing",
    "adopt.create.preview": f"{_ADOPT}:form_repository",
    "adopt.create.apply": f"{_ADOPT}:form_repository",
    "adopt.evolve-starter.preview": f"{_ADOPT}:propose_starter_evolution",
    "adopt.exit.preview": f"{_ADOPT}:leave_ethos",
    "adopt.exit.apply": f"{_ADOPT}:leave_ethos",
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


def invoke(command: str, root: Path, fields: Mapping[str, object] | CommandRequest) -> EthosResult:
    """Select one request's operation and run its implementation, or return the refusal unchanged.

    A mapping's `root` entry is dropped only when it is the `root` argument itself, as an SDK
    function's `locals()` passes it, so a caller's stray `root` key is still refused. Selection is
    pure and runs outside the failure normalization, which wraps the implementation alone.
    """
    if isinstance(fields, Mapping) and fields.get("root") is root:
        fields = {name: value for name, value in fields.items() if name != "root"}
    chosen = select_operation(command, fields)
    if isinstance(chosen, Refused):
        return chosen.result
    module, _separator, name = IMPLEMENTATIONS[chosen.operation.id].partition(":")
    implementation = getattr(import_module(module), name)
    return application_result(command)(implementation)(root, chosen.request)
