"""Shell command references for product-binding closure extraction."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path


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
    tokens = _split_command(command)
    return shlex.join(tokens) if tokens else command.strip()


def _split_command(command: str) -> tuple[str, ...]:
    try:
        return tuple(shlex.split(command))
    except ValueError:
        return ()


def shell_executables(
    text: str, npm_scripts: dict[str, set[str]], *, module_imports: set[str] | None = None
) -> set[str]:
    """Extract native executables and optionally collect Python module dependencies."""
    functions = {
        match.group(1)
        for line in text.splitlines()
        if (match := re.match(r"\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\)\s*\{", line))
    }
    executables = set()
    for line in _shell_candidate_lines(text):
        for tokens in _shell_command_segments(line):
            values = command_executables(tokens, npm_scripts, module_imports=module_imports)
            executables.update(value for value in values if value not in functions)
    return executables


def _shell_candidate_lines(text: str) -> list[str]:
    lines = []
    heredoc = ""
    array_depth = 0
    continued = ""
    for raw in text.splitlines():
        line = continued + raw if continued else raw.strip()
        continued = ""

        if heredoc:
            heredoc = "" if line == heredoc else heredoc
            continue
        if array_depth:
            array_depth += line.count("(") - line.count(")")
            continue
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split, lexer.commenters = True, "#"
        try:
            list(lexer)
        except ValueError as exc:
            continued = line[:-1] + " " if str(exc) == "No escaped character" else line + "\n"
            continue
        if re.match(r"[A-Za-z_]\w*=\(", line):
            array_depth = line.count("(") - line.count(")")
            continue
        if re.match(r"(?:function\s+)?[A-Za-z_]\w*\s*\(\)\s*\{", line):
            line = line.split("{", 1)[1].rsplit("}", 1)[0].strip()
        if match := re.search(r"<<-?\s*['\"]?([A-Za-z_]\w*)['\"]?", line):
            heredoc, line = match.group(1), line[: match.start()].rstrip()
        if line := _shell_command_line(line):
            lines.append(line)
    return lines


def _shell_command_segments(
    line: str, *, strict: bool = False, preserve_context: bool = False
) -> tuple[tuple[str, ...], ...]:
    lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split, lexer.commenters = True, "#"
    try:
        tokens = list(lexer)
    except ValueError:
        if strict:
            raise
        return ()
    for index, token in enumerate(tokens):
        if set(token) <= set("<>&") and ("<" in token or ">" in token):
            tokens[index] = ""
            if index + 1 < len(tokens) and not set(tokens[index + 1]) <= set(";&|()<>"):
                tokens[index + 1] = ""
    segments: list[tuple[str, ...]] = []
    start = 0
    for index, token in enumerate((*tokens, ";")):
        if not token or not set(token) <= set(";&|()<>"):
            continue
        segment = tuple(token for token in tokens[start:index] if token)
        start = index + 1
        command = segment if preserve_context else _shell_segment_command(segment)
        if command:
            segments.append(command)
    return tuple(segments)


def _shell_segment_command(tokens: tuple[str, ...]) -> tuple[str, ...]:
    command = _command_tokens(tokens, shell_context=True)
    return (
        command
        if command and command[0] not in _SHELL_NON_EXECUTABLES and not command[0].startswith("$")
        else ()
    )


def command_executables(
    tokens: tuple[str, ...],
    npm_scripts: dict[str, set[str]],
    *,
    trail: frozenset[str] = frozenset(),
    module_imports: set[str] | None = None,
) -> set[str]:
    """Separate OS executable identities from interpreter-loaded Python imports."""
    command = _command_tokens(tokens)
    if not command or not (executable := _executable_identity(command[0])):
        return set()
    executables = {executable}
    if (module := python_module(command)) and module_imports is not None:
        module_imports.add(module.partition(".")[0])
    child = _wrapped_command_tokens(command, executable)
    if child:
        executables.update(
            command_executables(child, npm_scripts, trail=trail, module_imports=module_imports)
        )
    if executable == "npm" and (script := _npm_script_name(command)) and script not in trail:
        for value in npm_scripts.get(script, set()):
            if script_tokens := _split_command(value):
                executables.update(
                    command_executables(
                        script_tokens,
                        npm_scripts,
                        trail=trail | {script},
                        module_imports=module_imports,
                    )
                )
    return executables


def _command_tokens(tokens: tuple[str, ...], *, shell_context: bool = False) -> tuple[str, ...]:
    """Native argv preserves its executable; shell syntax may prefix a command."""
    index = 0
    while index < len(tokens):
        if tokens[index] == "env":
            return _command_tokens(
                _tokens_after_options(
                    tokens[index + 1 :], _ENV_OPTIONS_WITH_VALUE, skip_assignments=True
                ),
                shell_context=shell_context,
            )
        if shell_context and tokens[index].rsplit("/", 1)[-1] in {"sudo", "nice", "nohup"}:
            name = tokens[index].rsplit("/", 1)[-1]
            options = (
                frozenset({"-u", "--user", "-g", "--group", "-p", "--prompt", "-h", "--host"})
                if name == "sudo"
                else frozenset({"-n", "--adjustment"})
                if name == "nice"
                else frozenset()
            )
            return _command_tokens(
                _tokens_after_options(tokens[index + 1 :], options), shell_context=True
            )
        if shell_context and (
            _SHELL_ASSIGNMENT.fullmatch(tokens[index])
            or tokens[index].startswith("-")
            or tokens[index].isdigit()
            or tokens[index] in _SHELL_PREFIXES
        ):
            index += 1
        else:
            break
    return tokens[index:]


def canonical_gate_command(command: tuple[str, ...]) -> tuple[str, ...]:
    """Remove only a host-specific absolute Python interpreter path."""
    if not command:
        return command
    head, *rest = command
    name = Path(head).name
    return ("python", *rest) if Path(head).is_absolute() and name.startswith("python") else command


def python_module(tokens: tuple[str, ...]) -> str:
    """Resolve the interpreter-selected module without loading candidate code."""
    executable = tokens[0].replace("\\", "/").rsplit("/", maxsplit=1)[-1] if tokens else ""
    if not re.fullmatch(r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?", executable):
        return ""
    index = 1
    while index < len(tokens):
        option = tokens[index]
        if option == "-m":
            return tokens[index + 1] if index + 1 < len(tokens) else ""
        if option.startswith("-m"):
            return option[2:]
        if (
            not option.startswith("-")
            or option.startswith("-c")
            or option in {"--", "-h", "--help", "-V", "--version"}
        ):
            return ""
        index += 2 if option in {"-W", "-X", "--check-hash-based-pycs"} else 1
    return ""


def _wrapped_command_tokens(tokens: tuple[str, ...], executable: str) -> tuple[str, ...]:
    if executable == "uv":
        run_index = next(
            (index for index, argument in enumerate(tokens[1:], 1) if argument == "run"), -1
        )
        return (
            _tokens_after_options(tokens[run_index + 1 :], _UV_RUN_OPTIONS_WITH_VALUE)
            if run_index >= 0
            else ()
        )
    if executable in {"npx", "uvx"}:
        value_options = _NPX_OPTIONS_WITH_VALUE if executable == "npx" else _UVX_OPTIONS_WITH_VALUE
        child = _tokens_after_options(tokens[1:], value_options)
        package_command = _package_command(child[0]) if child else ""
        return (package_command, *child[1:]) if package_command else ()
    return ()


def _tokens_after_options(
    tokens: tuple[str, ...], options_with_value: frozenset[str], *, skip_assignments: bool = False
) -> tuple[str, ...]:
    index = 0
    while index < len(tokens):
        argument = tokens[index]
        if argument.startswith((">", "<")):
            return ()
        if argument == "--":
            return tokens[index + 1 :]
        if skip_assignments and _SHELL_ASSIGNMENT.fullmatch(argument):
            index += 1
            continue
        if not argument.startswith("-"):
            return tokens[index:]
        option = argument.partition("=")[0]
        index += 2 if option in options_with_value and "=" not in argument else 1
    return ()


def _package_command(argument: str) -> str:
    package = argument
    if package.startswith("@") and "/" in package:
        package, separator, _ = package.rpartition("@")
        package = package if separator else argument
    elif "@" in package:
        package = package.partition("@")[0]
    return package.rsplit("/", maxsplit=1)[-1]


def _npm_script_name(tokens: tuple[str, ...]) -> str:
    args = _tokens_after_options(tokens[1:], _NPM_OPTIONS_WITH_VALUE)
    if not args or args[0] not in {"run", "run-script"}:
        return ""
    script = _tokens_after_options(args[1:], _NPM_OPTIONS_WITH_VALUE)
    return script[0] if script else ""


def _executable_identity(token: str) -> str:
    if token.startswith("/dev/"):
        return ""
    if token.startswith("/"):
        token = token.rsplit("/", maxsplit=1)[-1]
    elif "/" in token:
        return ""
    return token if re.fullmatch(r"[A-Za-z0-9_.+-]+", token) else ""


def _shell_command_line(line: str) -> str:
    if (
        not line
        or line.startswith(("#", "-", "for ((", "case "))
        or re.match(r"(?:function\s+)?\w+\s*\(\)\s*\{", line)
    ):
        return ""
    if match := re.match(
        r"[A-Za-z0-9_*-]+(?:\s*\|\s*[A-Za-z0-9_*-]+)*\)\s*(.*)$",
        line,
    ):
        line = match.group(1)
    return line.removeprefix("$").lstrip()


def shebang_executable(line: str) -> str:
    """Extract the executable identity from a shebang line."""
    tokens = _split_command(line.removeprefix("#!"))
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
        for line in _shell_candidate_lines(text)
        for tokens in _shell_command_segments(line)
        if (command := command_identity(tokens, known_commands, require_declared=require_declared))
    }


def command_invocation(text: str, vocabulary: CommandVocabulary | None = None) -> bool | None:
    """Classify positive invocation syntax without evaluating data or hiding ambiguity."""
    candidate = text.strip()
    if not candidate:
        return False
    if re.match(r"^(?:\$\s+|[\w.-]+@[\w.-]+(?::[^$#\s]+)?\$\s+)", candidate):
        return True
    try:
        segments = _shell_command_segments(candidate, strict=True, preserve_context=True)
    except ValueError:
        if re.search(r"[.!?]$", candidate) and not re.search(r"(?:^|\s)--?\w", candidate):
            return False
        return None
    outcomes = []
    for segment in segments:
        command = _command_tokens(segment, shell_context=True)
        if len(command) < 2 or command[0] == "$":
            continue
        result = _invocation_shape(command, vocabulary, candidate)
        if result is True:
            return True
        outcomes.append(result)
    return None if None in outcomes else False


def _invocation_shape(
    command: tuple[str, ...], vocabulary: CommandVocabulary | None, source: str
) -> bool | None:
    if vocabulary is not None and command_identity(command, vocabulary):
        return True
    child = _wrapped_command_tokens(command, _executable_identity(command[0]))
    if child:
        return True
    executable = command[0].replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.+-]*", executable):
        return False
    operand = command[1]
    if any(argument.startswith("-") for argument in command[1:]):
        return True
    if operand.startswith(("/", "./", "../", "$")) or "/" in operand:
        return None if re.search(r"[.!?]$", source) else True
    return False if re.search(r"[.!?]$", source) else None


def command_identity(
    tokens: tuple[str, ...],
    known_commands: set[str] | CommandVocabulary,
    *,
    require_declared: bool = False,
) -> str:
    """Resolve a token sequence to a declared or unowned command identity."""
    command = _command_tokens(tokens)
    if not command:
        return ""
    executable = _executable_identity(command[0])
    child = _wrapped_command_tokens(command, executable)
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


_SHELL_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")

_SHELL_PREFIXES = {
    "!",
    "command",
    "do",
    "elif",
    "else",
    "env",
    "exec",
    "if",
    "sudo",
    "then",
    "time",
}

_SHELL_NON_EXECUTABLES = {
    "[",
    "[[",
    "break",
    "case",
    "cd",
    "continue",
    "declare",
    "done",
    "echo",
    "esac",
    "eval",
    "exit",
    "export",
    "false",
    "fi",
    "for",
    "local",
    "printf",
    "read",
    "readonly",
    "return",
    "set",
    "shift",
    "shopt",
    "source",
    "test",
    "trap",
    "true",
    "typeset",
    "ulimit",
    "umask",
    "unset",
    "until",
    "wait",
    "while",
}

_UV_RUN_OPTIONS_WITH_VALUE = frozenset(
    {
        "--cache-dir",
        "--config-file",
        "--config-setting",
        "--directory",
        "--env-file",
        "--exclude-newer",
        "--group",
        "--index",
        "--link-mode",
        "--package",
        "--project",
        "--python",
        "--resolution",
        "--with",
    }
)

_NPX_OPTIONS_WITH_VALUE = frozenset({"--cache", "--call", "--package", "-c", "-p"})

_UVX_OPTIONS_WITH_VALUE = frozenset(
    {"--from", "--index", "--python", "--refresh-package", "--with"}
)

_NPM_OPTIONS_WITH_VALUE = frozenset({"--prefix", "--workspace", "-w"})

_ENV_OPTIONS_WITH_VALUE = frozenset({"--chdir", "--unset", "-C", "-u"})


def shell_configuration_inputs(text: str) -> tuple[set[str], bool]:
    """Observe explicit native Prettier config inputs, retaining dynamic uncertainty.

    This covers --config and --ignore-path, not arbitrary shell effects. Native
    command wrappers use the existing executable resolver. Changed directories,
    substitutions and malformed shell cannot be treated as resolved paths.
    """
    inputs: set[str] = set()
    unknown = False
    try:
        segments = _shell_command_segments(text, strict=True, preserve_context=True)
    except ValueError:
        return inputs, True
    changed_directory = False
    for tokens in segments:
        changed_directory |= tokens[0] in {"cd", "pushd", "popd"} or (
            tokens[0] == "env"
            and any(token.partition("=")[0] in {"-C", "--chdir"} for token in tokens[1:])
        )
        command = _shell_segment_command(tokens)
        while command and (wrapped := _wrapped_command_tokens(command, command[0])):
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
