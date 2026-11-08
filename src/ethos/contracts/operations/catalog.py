"""The root operation catalog: every root command's declared operations, and their argv reading.

Every transport selects through these declarations, and `next` classifies a rendered root argv by
them, so a step names the operation it runs and carries that operation's effects and authority.
"""

from collections.abc import Sequence

from ethos.contracts.operations import adopt
from ethos.contracts.operations import land
from ethos.contracts.operations import plan
from ethos.contracts.operations import prove
from ethos.contracts.operations import publish
from ethos.contracts.operations import status
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import Operation

COMMANDS: dict[str, Command] = {
    module.COMMAND.name: module.COMMAND for module in (status, plan, prove, land, publish, adopt)
}
# Options every root command takes besides its request: the bound root and the JSON frame.
_ROOT_FLAG, _JSON_FLAG = "--root", "--json"


def select_argv(argv: Sequence[str]) -> tuple[Command, Operation | None] | None:
    """Return the root command an ETHOS argv runs and the operation it selects, if any.

    A boolean selector counts only as its bare flag and a valued field as `--flag value` or
    `--flag=value`; anything else, such as `--flag=false`, leaves the argv unselected.
    """
    command = COMMANDS.get(argv[1]) if len(argv) > 1 else None
    if command is None:
        return None
    names = {command.flag(name): name for name in command.request.model_fields}
    present: set[str] = set()
    tokens = iter(argv[2:])
    for token in tokens:
        flag, equals = token.partition("=")[:2]
        name = names.get(flag)
        if flag == _ROOT_FLAG or (name is not None and command.valued(name)):
            if not equals and next(tokens, None) is None:
                return command, None
        elif equals or (name is None and token != _JSON_FLAG):
            return command, None
        if name is not None:
            present.add(name)
    return command, command.select(frozenset(present)).operation
