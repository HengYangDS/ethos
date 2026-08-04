"""Shell command references for product-binding closure extraction."""

from __future__ import annotations

import re
import shlex


def normalize_command(command: str) -> str:
    """Return one whitespace-normalized command identity without dropping options."""
    try:
        return shlex.join(shlex.split(command))
    except ValueError:
        return command.strip()


def shell_executables(text: str, npm_scripts: dict[str, set[str]]) -> set[str]:
    """Extract executable identities from shell command lines."""
    functions = {
        match.group(1)
        for line in text.splitlines()
        if (match := re.match(r"\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\)\s*\{", line))
    }
    executables = set()
    for line in _shell_candidate_lines(text):
        for tokens in _shell_command_segments(line):
            values = command_executables(tokens, npm_scripts)
            executables.update(value for value in values if value not in functions)
    return executables


def _shell_candidate_lines(text: str) -> list[str]:
    lines = []
    heredoc = ""
    array_depth = 0
    for raw in text.splitlines():
        line = raw.strip()
        if heredoc:
            heredoc = "" if line == heredoc else heredoc
            continue
        if array_depth:
            array_depth += line.count("(") - line.count(")")
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


def _shell_command_segments(line: str) -> tuple[tuple[str, ...], ...]:
    lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split, lexer.commenters = True, "#"
    try:
        tokens = list(lexer)
    except ValueError:
        return ()
    segments: list[tuple[str, ...]] = []
    start = 0
    for index, token in enumerate((*tokens, ";")):
        if token not in _SHELL_SEPARATORS:
            continue
        segment = tuple(tokens[start:index])
        start = index + 1
        command = _shell_segment_command(segment)
        if command:
            segments.append(command)
    return tuple(segments)


def _shell_segment_command(tokens: tuple[str, ...]) -> tuple[str, ...]:
    for index, argument in enumerate(tokens):
        if argument == "env":
            command_index = _env_command_start(tokens, index + 1)
            return tokens[command_index:] if command_index < len(tokens) else ()
        if _ignored_shell_token(argument):
            continue
        if argument in _SHELL_NON_EXECUTABLES or argument.startswith("$"):
            return ()
        return tokens[index:]
    return ()


def command_executables(
    tokens: tuple[str, ...],
    npm_scripts: dict[str, set[str]],
    *,
    trail: frozenset[str] = frozenset(),
) -> set[str]:
    """Extract an executable and any wrapped child executable identities."""
    command = _command_tokens(tokens)
    if not command or not (executable := _executable_identity(command[0])):
        return set()
    executables = {executable}
    child = _wrapped_command_tokens(command, executable)
    if child:
        executables.update(command_executables(child, npm_scripts, trail=trail))
    if executable == "npm" and (script := _npm_script_name(command)) and script not in trail:
        for value in npm_scripts.get(script, set()):
            try:
                script_tokens = tuple(shlex.split(value))
            except ValueError:
                continue
            executables.update(
                command_executables(script_tokens, npm_scripts, trail=trail | {script})
            )
    return executables


def _command_tokens(tokens: tuple[str, ...]) -> tuple[str, ...]:
    index = 0
    while index < len(tokens):
        argument = tokens[index]
        if argument == "env":
            index = _env_command_start(tokens, index + 1)
            continue
        if (
            argument in _SHELL_PREFIXES
            or argument in {"(", ")"}
            or _SHELL_ASSIGNMENT.fullmatch(argument)
            or argument.startswith("-")
            or argument.isdigit()
        ):
            index += 1
            continue
        return tokens[index:]
    return ()


def _env_command_start(tokens: tuple[str, ...], index: int) -> int:
    while index < len(tokens):
        argument = tokens[index]
        if argument == "--":
            return index + 1
        if _SHELL_ASSIGNMENT.fullmatch(argument):
            index += 1
            continue
        option = argument.partition("=")[0]
        if option in _ENV_OPTIONS_WITH_VALUE:
            index += 1 if "=" in argument else 2
            continue
        if argument.startswith("-"):
            index += 1
            continue
        return index
    return index


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
    if executable in {"python", "python3"} or re.fullmatch(r"python\d+(?:\.\d+)*", executable):
        module_index = next(
            (index for index, argument in enumerate(tokens[1:], 1) if argument == "-m"), -1
        )
        return tokens[module_index + 1 : module_index + 2] if module_index >= 0 else ()
    if executable in {"npx", "uvx"}:
        value_options = _NPX_OPTIONS_WITH_VALUE if executable == "npx" else _UVX_OPTIONS_WITH_VALUE
        child = _tokens_after_options(tokens[1:], value_options)
        package_command = _package_command(child[0]) if child else ""
        return (package_command, *child[1:]) if package_command else ()
    return ()


def _tokens_after_options(
    tokens: tuple[str, ...], options_with_value: frozenset[str]
) -> tuple[str, ...]:
    index = 0
    while index < len(tokens):
        argument = tokens[index]
        if argument.startswith((">", "<")):
            return ()
        if argument == "--":
            return tokens[index + 1 :]
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
    if match := re.match(r"[A-Za-z0-9_*-]+(?:\|[A-Za-z0-9_*-]+)*\)\s*(.*)$", line):
        line = match.group(1)
    return line.removeprefix("$").lstrip()


def _ignored_shell_token(token: str) -> bool:
    return bool(
        _SHELL_ASSIGNMENT.fullmatch(token)
        or token.startswith("-")
        or token.isdigit()
        or token in _SHELL_PREFIXES
    )


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
    known_commands: set[str],
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


def command_identity(
    tokens: tuple[str, ...],
    known_commands: set[str],
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
    candidates = []
    for known in known_commands:
        try:
            known_tokens = tuple(shlex.split(known))
        except ValueError:
            continue
        if command[: len(known_tokens)] == known_tokens:
            candidates.append((len(known_tokens), known))
    if candidates:
        return max(candidates)[1]
    roots = {known.partition(" ")[0] for known in known_commands}
    if not require_declared or executable not in roots:
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

_SHELL_SEPARATORS = {"&", "&&", ";", ";;", "|", "||"}

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
