"""Build every catalog command from its declaration, and run the operation a request selects.

A command's parameters are its request's fields, positionals first, spelled as the catalog spells
them with no negated forms, then `--root` and `--json`. Running one selects its operation through
the shared selection, binds the root that operation needs and exits as it declares, and
`--help --json` prints the same declarations as data. Only the commands under the invoked word are
built.
"""

import inspect
from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import cast

from cyclopts import App
from cyclopts import Parameter

from ethos.application.catalog import Refused
from ethos.application.catalog import invoke
from ethos.application.catalog import select_operation
from ethos.application.catalog import usage_refusal
from ethos.application.console import resolve_root
from ethos.contracts.operations.catalog import COMMANDS
from ethos.contracts.operations.catalog import GROUPS
from ethos.contracts.operations.catalog import command_path
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption

_KEYWORD = inspect.Parameter.KEYWORD_ONLY
# The options every command takes besides its request: the bound root and the JSON frame.
_OPTIONS = (
    inspect.Parameter("root", _KEYWORD, default=None, annotation=RootOption | None),
    inspect.Parameter("json_output", _KEYWORD, default=False, annotation=JsonFlag),
)


def _help(command: Command) -> str:
    """Render one command's help: its summary and each operation with the flags that select it."""
    lines = [command.summary, "", "Each operation runs when exactly its flags are given:", ""]
    for item in command.operations:
        flags = [command.flag(name) for name, want in item.selectors if want in {"true", "set"}]
        selected = f" (`{' '.join(flags)}`)" if flags else ""
        lines.append(f"- `{item.id}`{selected}: {item.summary}")
    return "\n".join(lines)


def _flags(command: Command) -> Parameter:
    """Spell one command's fields as the catalog declares them, with no negated forms."""
    return Parameter(negative=(), name_transform=lambda field: command.flag(field)[2:])


def _parameter(command: Command, name: str) -> inspect.Parameter:
    """Return one request field as the parameter Cyclopts reads, with its help text."""
    info = command.request.model_fields[name]
    # The field's type, known only at run time, as the annotation Cyclopts converts a value to.
    annotation: Any = info.annotation
    return inspect.Parameter(
        name,
        inspect.Parameter.POSITIONAL_OR_KEYWORD if name in command.positionals else _KEYWORD,
        default=inspect.Parameter.empty if info.is_required() else info.default,
        annotation=Annotated[
            annotation,
            Parameter(help=info.description or "", allow_leading_hyphen=name in command.hyphen),
        ],
    )


def _signature(command: Command) -> inspect.Signature:
    """Return the parameters Cyclopts reads: positional fields, keyword-only fields, the options."""
    fields = [name for name in command.request.model_fields if name not in command.positionals]
    named = [_parameter(command, name) for name in (*command.positionals, *fields)]
    return inspect.Signature([*named, *_OPTIONS])


def run(
    name: str,
    request: Mapping[str, object] | CommandRequest,
    root: Path | None,
    *,
    json_output: bool,
) -> None:
    """Run the operation one request selects, or report why it selects none."""
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
    result = invoke(name, target, chosen.request)
    status = result.data.get("exit_status") if operation.exit == "process" else None
    if isinstance(status, int):
        raise SystemExit(status)
    emit(
        result,
        json_output=json_output,
        enforce=operation.exit != "observe",
        artifact_root=None if operation.creates_root else target,
    )


def _function(command: Command) -> Callable[..., None]:
    """Return the function Cyclopts calls for one command, with the signature it reads."""
    signature = _signature(command)

    def call(*args: object, **kwargs: object) -> None:
        fields = signature.bind(*args, **kwargs).arguments
        root = cast("Path | None", fields.pop("root", None))
        run(command.name, fields, root, json_output=bool(fields.pop("json_output", False)))

    vars(call)["__signature__"] = signature
    return call


def _group(words: Sequence[str]) -> App:
    """Return the Cyclopts application of one path prefix, declaring each missing level."""
    parent = app
    for depth, word in enumerate(words, start=1):
        if word not in parent:
            group = GROUPS[" ".join(words[:depth])]
            parent.command(App(name=word, help=group.help, show=not group.hidden))
        parent = parent[word]
    return parent


def register(word: str = "") -> None:
    """Declare the catalog commands whose path starts with one word, or every one for none."""
    for name, command in COMMANDS.items():
        *prefix, leaf = name.split()
        if word in {"", name.split()[0]} and leaf not in (group := _group(prefix)):
            group.command(
                _function(command),
                name=leaf,
                help=_help(command),
                default_parameter=_flags(command),
            )


def help_result(words: Sequence[str]) -> EthosResult:
    """Return the catalog of the command or group the words name, or of every root command."""
    named = command_path(words)
    first = words[0] if words else ""
    group = [item for item in COMMANDS.values() if item.name.split()[0] == first]
    roots = [item for item in COMMANDS.values() if " " not in item.name]
    commands = [named] if named else group or roots
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
