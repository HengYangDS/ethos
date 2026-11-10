"""The operation catalog: every command's declared operations, and their argv reading.

Every transport selects through these declarations, and `next` classifies a rendered ETHOS argv by
them, so a step names the operation it runs and carries that operation's effects and authority. A
command is keyed by its path of up to three words, and `GROUPS` declares each prefix of a path.
"""

from collections.abc import Sequence
from itertools import takewhile
from typing import get_origin

from ethos.contracts.operations.adopt import ADOPT
from ethos.contracts.operations.attestation import ATTESTATION
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import Group
from ethos.contracts.operations.declaration import Operation
from ethos.contracts.operations.host import HOST_RUN
from ethos.contracts.operations.land import LAND
from ethos.contracts.operations.plan import PLAN
from ethos.contracts.operations.prove import PROVE
from ethos.contracts.operations.publish import PUBLISH
from ethos.contracts.operations.status import STATUS

COMMANDS: dict[str, Command] = {
    command.name: command
    for command in (STATUS, PLAN, PROVE, LAND, PUBLISH, ADOPT, *ATTESTATION, HOST_RUN)
}
GROUPS: dict[str, Group] = {
    group.name: group
    for group in (
        Group(name="attestation", help="Record or query the sole Git-native Attestation set."),
        Group(name="host", help="Admit heavy local work through the host's one queue."),
    )
}
# Options every command takes besides its request: the bound root and the JSON frame; after the
# end of options, every token is a word.
_ROOT_FLAG, _JSON_FLAG, _END = "--root", "--json", "--"


def command_path(words: Sequence[str]) -> Command | None:
    """Return the command that the longest prefix of up to three words names, if any."""
    paths = (" ".join(words[:count]) for count in (3, 2, 1))
    return next((COMMANDS[path] for path in paths if path in COMMANDS), None)


def _positional(command: Command, index: int) -> str | None:
    """Return the field a command line's word at one index binds; a last tuple takes the rest."""
    if index < len(command.positionals):
        return command.positionals[index]
    last = command.positionals[-1:]
    variadic = bool(last) and get_origin(command.request.model_fields[last[0]].annotation) is tuple
    return last[0] if variadic else None


def select_argv(argv: Sequence[str]) -> tuple[Command, Operation | None] | None:
    """Return the command an ETHOS argv runs and the operation it selects, if any.

    A boolean selector counts only as its bare flag and a valued field as `--flag value` or
    `--flag=value`. A word, or each token after `--`, binds the next positional field, and a field
    that takes a leading hyphen also takes an unknown option. Anything else, such as `--flag=false`,
    a word no field takes or a field given both ways, leaves the argv unselected.
    """
    command = command_path(list(takewhile(lambda word: not word.startswith("-"), argv[1:4])))
    if command is None:
        return None
    names = {command.flag(name): name for name in command.request.model_fields}
    present: set[str] = set()
    words: list[str] = []
    tokens = iter(argv[1 + len(command.name.split()) :])
    for token in tokens:
        flag, equals = token.partition("=")[:2]
        name = names.get(flag)
        unknown = name is None and flag not in {_ROOT_FLAG, _JSON_FLAG}
        if (
            token == _END
            or not token.startswith("-")
            or (unknown and _positional(command, len(words)) in command.hyphen)
        ):
            words.extend(tokens if token == _END else (token,))
            continue
        if flag == _ROOT_FLAG or (name is not None and command.valued(name)):
            if not equals and next(tokens, None) is None:
                return command, None
        elif equals or unknown:
            return command, None
        if name is not None:
            present.add(name)
    owners = {_positional(command, index) or "" for index in range(len(words))}
    if "" in owners or owners & present:
        return command, None
    return command, command.select(frozenset(present | owners)).operation
