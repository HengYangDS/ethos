"""The operation catalog: every command's declared operations, and their argv reading.

Every transport selects through these declarations, and `next` classifies a rendered ETHOS argv by
them, so a step names the operation it runs and carries that operation's effects and authority. A
command is keyed by its path of up to three words, and `GROUPS` declares each prefix of a path.
"""

from collections.abc import Iterator
from collections.abc import Sequence
from itertools import takewhile
from typing import get_origin

from ethos.contracts.operations.adopt import ADOPT
from ethos.contracts.operations.attestation import ATTESTATION
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import Group
from ethos.contracts.operations.declaration import Operation
from ethos.contracts.operations.hook import HOOK
from ethos.contracts.operations.host import HOST_RUN
from ethos.contracts.operations.land import LAND
from ethos.contracts.operations.lane import LANE
from ethos.contracts.operations.lane_repair import LANE_REPAIR
from ethos.contracts.operations.plan import PLAN
from ethos.contracts.operations.prove import PROVE
from ethos.contracts.operations.publish import PUBLISH
from ethos.contracts.operations.status import STATUS

_ROOTS = (STATUS, PLAN, PROVE, LAND, PUBLISH, ADOPT)
COMMANDS: dict[str, Command] = {
    command.name: command
    for command in (*_ROOTS, *ATTESTATION, HOST_RUN, *HOOK, *LANE, *LANE_REPAIR)
}
GROUPS: dict[str, Group] = {
    group.name: group
    for group in (
        Group(name="attestation", help="Record or query the sole Git-native Attestation set."),
        Group(name="host", help="Admit heavy local work through the host's one queue."),
        Group(name="hook", help="Hook admission and guard reports.", hidden=True),
        Group(name="lane", help="Work Lane lifecycle and write admission.", hidden=True),
        Group(name="lane redact", help="Redact protected peer identity in a lane's records."),
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
    bound = _bound_fields(command, argv[1 + len(command.name.split()) :])
    if bound is None:
        return command, None
    present, words = bound
    owners = {_positional(command, index) or "" for index in range(len(words))}
    if "" in owners or owners & present:
        return command, None
    return command, command.select(frozenset(present | owners)).operation


def _bound_fields(command: Command, rest: Sequence[str]) -> tuple[set[str], list[str]] | None:
    """Split the tokens after a command path into its present fields and positional words.

    None means the tokens leave the argv unselected: a valued flag without its value, a value on a
    boolean selector, or an option the command does not declare.
    """
    names = {command.flag(name): name for name in command.request.model_fields}
    present: set[str] = set()
    words: list[str] = []
    tokens = iter(rest)
    for token in tokens:
        flag, equals = token.partition("=")[:2]
        name = names.get(flag)
        unknown = name is None and flag not in {_ROOT_FLAG, _JSON_FLAG}
        if _is_word(command, token, unknown=unknown, position=len(words)):
            words.extend(tokens if token == _END else (token,))
        elif not _option_admitted(
            command, flag, name, equals=equals, unknown=unknown, tokens=tokens
        ):
            return None
        elif name is not None:
            present.add(name)
    return present, words


def _is_word(command: Command, token: str, *, unknown: bool, position: int) -> bool:
    """Whether a token binds a positional field rather than naming an option."""
    if token == _END or not token.startswith("-"):
        return True
    return unknown and _positional(command, position) in command.hyphen


def _option_admitted(
    command: Command,
    flag: str,
    name: str | None,
    *,
    equals: str,
    unknown: bool,
    tokens: Iterator[str],
) -> bool:
    """Whether an option is admitted, consuming its separate value when it takes one.

    `--root` and every valued field take a value, inline after `=` or as the next token; a boolean
    selector or `--json` takes none, so a value on it or an undeclared option leaves the argv
    unselected.
    """
    if flag == _ROOT_FLAG or (name is not None and command.valued(name)):
        return bool(equals) or next(tokens, None) is not None
    return not equals and not unknown
