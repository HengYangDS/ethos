"""Compile command references and declared CLI vocabulary through native syntax."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

from ethos.repository.policy.references.commands import invocation
from ethos.repository.policy.references.commands import syntax


@dataclass(frozen=True, slots=True)
class CommandVocabulary:
    """One immutable tokenization of declared command identities."""

    identities: tuple[tuple[tuple[str, ...], str], ...]
    groups: frozenset[str]
    roots: frozenset[str]

    @classmethod
    def compile(cls, commands: set[str]) -> CommandVocabulary:
        """Compile normalized command identities once for repeated matching."""
        identities = tuple(
            sorted(
                ((tokens, command) for command in commands if (tokens := _split_command(command))),
                key=lambda item: (len(item[0]), item[1]),
                reverse=True,
            )
        )
        groups = frozenset(
            identity
            for tokens, identity in identities
            if any(
                other[: len(tokens)] == tokens and len(other) > len(tokens)
                for other, _ in identities
            )
        )
        return cls(
            identities=identities,
            groups=groups,
            roots=frozenset(tokens[0] for tokens, _ in identities),
        )


def normalize_command(command: str) -> str:
    """Return one whitespace-normalized command identity without dropping options."""
    try:
        return shlex.join(shlex.split(command))
    except ValueError:
        return command.strip()


def _split_command(command: str) -> tuple[str, ...]:
    try:
        return tuple(shlex.split(command))
    except ValueError:
        return ()


def shell_executables(
    text: str,
    npm_scripts: dict[str, set[str]],
    *,
    module_imports: set[str] | None = None,
    trail: frozenset[str] = frozenset(),
    unresolved: set[str] | None = None,
) -> set[str]:
    """Extract native executables and optionally collect Python module dependencies."""
    functions = {
        match.group(1)
        for line in text.splitlines()
        if (match := re.match(r"\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\)\s*\{", line))
    }
    executables = set()
    for line in syntax.candidate_lines(text):
        for tokens in syntax.command_segments(line):
            values = command_executables(
                syntax.command_tokens(tokens),
                npm_scripts,
                module_imports=module_imports,
                trail=trail,
                unresolved=unresolved,
            )
            executables.update(value for value in values if value not in functions)
    return executables


def command_executables(
    tokens: tuple[str, ...] | invocation.ArgumentVector,
    npm_scripts: dict[str, set[str]],
    *,
    trail: frozenset[str] = frozenset(),
    module_imports: set[str] | None = None,
    unresolved: set[str] | None = None,
) -> set[str]:
    """Separate OS executable identities from interpreter-loaded Python imports."""
    arguments = (
        tokens
        if isinstance(tokens, invocation.ArgumentVector)
        else invocation.ArgumentVector(tokens)
    )
    gaps = unresolved if unresolved is not None else set()
    command = arguments.words
    if not command or command[0] is None:
        gaps.add("executable")
        return set()
    if not (executable := invocation.executable_identity(command[0])):
        return set()
    executables = {executable}
    module = invocation.python_module(command, executable, open_tail=arguments.open_tail)
    if module is None:
        gaps.add("import")
    elif module and module_imports is not None:
        module_imports.add(module.partition(".")[0])
    child = invocation.child_tokens(command, executable, open_tail=arguments.open_tail)
    if child is None:
        gaps.add("executable")
    elif child:
        executables.update(
            command_executables(
                invocation.ArgumentVector(child, open_tail=arguments.open_tail),
                npm_scripts,
                trail=trail,
                module_imports=module_imports,
                unresolved=gaps,
            )
        )
    script = (
        invocation.npm_script_name(command, open_tail=arguments.open_tail)
        if executable == "npm"
        else ""
    )
    if script is None:
        gaps.add("executable")
    elif script and script not in trail:
        for value in npm_scripts.get(script, set()):
            executables.update(
                shell_executables(
                    value,
                    npm_scripts,
                    trail=trail | {script},
                    module_imports=module_imports,
                    unresolved=gaps,
                )
            )
    return executables


def shebang_executable(line: str) -> str:
    """Extract the executable identity from a shebang line."""
    try:
        tokens = shlex.split(line.removeprefix("#!"))
    except ValueError:
        return ""
    if not tokens:
        return ""
    executable = tokens[0].rsplit("/", maxsplit=1)[-1]
    return tokens[1] if executable == "env" and len(tokens) > 1 else executable


def shell_commands(
    text: str,
    known_commands: set[str] | CommandVocabulary,
    *,
    require_declared: bool = False,
) -> set[str]:
    """Extract known command identities from shell command lines."""
    return {
        command
        for line in syntax.candidate_lines(text)
        for tokens in syntax.command_segments(line)
        if (command := command_identity(tokens, known_commands, require_declared=require_declared))
    }


def command_identity(
    tokens: tuple[str, ...],
    known_commands: set[str] | CommandVocabulary,
    *,
    require_declared: bool = False,
) -> str:
    """Resolve a token sequence to a declared or unowned command identity."""
    command = syntax.command_tokens(tokens)
    if not command:
        return ""
    executable = invocation.executable_identity(command[0])
    child = invocation.child_tokens(command, executable)
    if child:
        return command_identity(child, known_commands, require_declared=require_declared)
    vocabulary = (
        known_commands
        if isinstance(known_commands, CommandVocabulary)
        else CommandVocabulary.compile(known_commands)
    )
    match = next(
        (
            (identity_tokens, identity)
            for identity_tokens, identity in vocabulary.identities
            if command[: len(identity_tokens)] == identity_tokens
        ),
        None,
    )
    if match is not None:
        identity_tokens, identity = match
        remaining = command[len(identity_tokens) :]
        if (
            not require_declared
            or identity not in vocabulary.groups
            or not remaining
            or remaining[0].startswith("-")
        ):
            return identity
    if not require_declared or executable not in vocabulary.roots:
        return ""
    path = tuple(
        argument
        for argument in command
        if not argument.startswith("-")
        and re.fullmatch(r"[A-Za-z0-9_.+-]+", argument)
        and re.search(r"[A-Za-z0-9]", argument)
    )
    if len(path) > 1:
        return shlex.join(path)
    return ""


def shell_configuration_inputs(text: str) -> tuple[set[str], bool]:
    """Observe explicit native Prettier config inputs, retaining dynamic uncertainty.

    This covers --config and --ignore-path, not arbitrary shell effects. Native
    command wrappers use the existing executable resolver. Changed directories,
    substitutions and malformed shell cannot be treated as resolved paths.
    """
    inputs: set[str] = set()
    unknown = False
    try:
        segments = syntax.command_segments(text, strict=True, preserve_context=True)
    except ValueError:
        return inputs, True
    changed_directory = False
    for tokens in segments:
        changed_directory |= tokens[0] in {"cd", "pushd", "popd"} or (
            tokens[0] == "env"
            and any(token.partition("=")[0] in {"-C", "--chdir"} for token in tokens[1:])
        )
        command = syntax.command_tokens(tokens)
        while command and (wrapped := invocation.child_tokens(command, command[0])):
            if wrapped == command:
                break
            command = wrapped
        if not command or command[0].rsplit("/", 1)[-1] != "prettier":
            continue
        values, invalid = _prettier_configuration_options(command)
        unknown |= invalid
        for value in values:
            if changed_directory or any(token in value for token in ("$", "`", "*", "?", "~")):
                unknown = True
            else:
                inputs.add(value)
    return inputs, unknown


def _prettier_configuration_options(command: tuple[str, ...]) -> tuple[set[str], bool]:
    """Read explicit native options, not arbitrary occurrences of path strings."""
    unknown = False
    values: dict[str, str] = {}
    ignored: set[str] = set()
    index = 1
    while index < len(command):
        argument = command[index]
        if argument == "--":
            break
        option, separator, value = argument.partition("=")
        index += 1
        if option == "--no-config":
            values.pop("--config", None)
        if option not in {"--config", "--ignore-path"}:
            continue
        if not separator:
            value = command[index] if index < len(command) else ""
            index += 1
        if not value or value.startswith("-"):
            unknown = True
        elif option == "--ignore-path":
            ignored.add(value)
        else:
            values[option] = value
    return {*values.values(), *ignored}, unknown
