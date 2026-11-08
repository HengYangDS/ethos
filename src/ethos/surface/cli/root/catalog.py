"""Build the six root commands from the operation catalog.

Each command flattens its kernel request model into the flags the catalog spells, with no negated
forms. Running it selects the operation through the shared selection, binds the root that operation
needs and exits as it declares; `--help --json` prints the same declarations as data.
"""

from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from ethos.application.catalog import Refused
from ethos.application.catalog import invoke
from ethos.application.catalog import select_operation
from ethos.application.catalog import usage_refusal
from ethos.contracts.operations import COMMANDS
from ethos.contracts.operations.adopt import AdoptRequest
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.land import LandRequest
from ethos.contracts.operations.plan import PlanRequest
from ethos.contracts.operations.prove import ProofRequest
from ethos.contracts.operations.publish import PublishRequest
from ethos.contracts.operations.status import StatusRequest
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

_STATUS, _PLAN, _PROVE = StatusRequest(), PlanRequest(), ProofRequest()
_LAND, _PUBLISH, _ADOPT = LandRequest(), PublishRequest(), AdoptRequest()


def _help(name: str) -> str:
    """Render one command's help: its summary and each operation with the flags that select it."""
    command = COMMANDS[name]
    lines = [command.summary, "", "Each operation runs when exactly its flags are given:", ""]
    for item in command.operations:
        flags = [command.flag(name) for name, want in item.selectors if want in {"true", "set"}]
        selected = f" (`{' '.join(flags)}`)" if flags else ""
        lines.append(f"- `{item.id}`{selected}: {item.summary}")
    return "\n".join(lines)


def _flags(name: str) -> Parameter:
    """Spell one command's fields as the catalog declares them, with no negated forms."""
    command = COMMANDS[name]
    return Parameter(negative=(), name_transform=lambda field: command.flag(field)[2:])


def _run(name: str, request: CommandRequest, root: Path | None, *, json_output: bool) -> None:
    """Run the operation one parsed request selects, or report why it selects none."""
    chosen = select_operation(name, request)
    if isinstance(chosen, Refused):
        emit(chosen.result, json_output=json_output)
        return
    operation = chosen.operation
    if operation.creates_root and root is None:
        refusal = usage_refusal(name, ("formation_root_required",), {"operation": operation.id})
        emit(refusal, json_output=json_output)
        return
    target = root if operation.creates_root and root is not None else resolve_root(root)
    emit(
        invoke(name, target, chosen.request),
        json_output=json_output,
        enforce=operation.exit == "verdict",
        artifact_root=None if operation.creates_root else target,
    )


@app.command(help=_help("status"), default_parameter=_flags("status"))
def status(
    request: Annotated[StatusRequest, Parameter(name="*")] = _STATUS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    _run("status", request, root, json_output=json_output)


@app.command(help=_help("plan"), default_parameter=_flags("plan"))
def plan(
    request: Annotated[PlanRequest, Parameter(name="*")] = _PLAN,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    _run("plan", request, root, json_output=json_output)


@app.command(help=_help("prove"), default_parameter=_flags("prove"))
def prove(
    request: Annotated[ProofRequest, Parameter(name="*")] = _PROVE,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    _run("prove", request, root, json_output=json_output)


@app.command(help=_help("land"), default_parameter=_flags("land"))
def land(
    request: Annotated[LandRequest, Parameter(name="*")] = _LAND,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    _run("land", request, root, json_output=json_output)


@app.command(help=_help("publish"), default_parameter=_flags("publish"))
def publish(
    request: Annotated[PublishRequest, Parameter(name="*")] = _PUBLISH,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    _run("publish", request, root, json_output=json_output)


@app.command(help=_help("adopt"), default_parameter=_flags("adopt"))
def adopt(
    request: Annotated[AdoptRequest, Parameter(name="*")] = _ADOPT,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    _run("adopt", request, root, json_output=json_output)


def help_result(name: str) -> EthosResult:
    """Return the catalog of one root command, or of every root command, as one result."""
    commands = [COMMANDS[name]] if name in COMMANDS else list(COMMANDS.values())
    return EthosResult(
        command="help",
        verdict="pass",
        state="described",
        summary={"operation_count": sum(len(item.operations) for item in commands)},
        data={
            "commands": [
                {
                    "name": command.name,
                    "summary": command.summary,
                    "flags": {field: command.flag(field) for field in command.request.model_fields},
                    "request_schema": command.request.model_json_schema(),
                    "operations": [
                        {
                            "id": item.id,
                            "summary": item.summary,
                            "selectors": dict(item.selectors),
                            "request": sorted(item.request),
                            "effects": list(item.effects),
                            "destructive": item.destructive,
                            "authorization": item.authorization,
                            "exit": item.exit,
                            "creates_root": item.creates_root,
                        }
                        for item in command.operations
                    ],
                }
                for command in commands
            ]
        },
    )
