"""Shell words and statement selection; no argv or policy inference."""

from __future__ import annotations

import re
import shlex


def candidate_lines(text: str) -> list[str]:
    lines = []
    heredoc = ""
    array_depth = 0
    continued = ""
    for raw in text.splitlines():
        line = continued + raw.strip()
        continued = ""

        if heredoc:
            heredoc = "" if line == heredoc else heredoc
            continue
        if array_depth:
            array_depth += line.count("(") - line.count(")")
            continue
        if len(line) - len(line.rstrip("\\")) & 1:
            continued = line[:-1] + " "
            continue
        if re.match(r"[A-Za-z_]\w*(?:\+)?=\(", line):
            array_depth = line.count("(") - line.count(")")
            continue
        if re.match(r"(?:function\s+)?[A-Za-z_]\w*\s*\(\)\s*\{", line):
            line = line.split("{", 1)[1].rsplit("}", 1)[0].strip()
        if match := re.search(r"<<-?\s*['\"]?([A-Za-z_]\w*)['\"]?", line):
            heredoc, line = match.group(1), line[: match.start()].rstrip()
        if line := _shell_command_line(line):
            lines.append(line)
    return lines


def command_segments(
    line: str, *, strict: bool = False, preserve_context: bool = False
) -> tuple[tuple[str, ...], ...]:
    lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split, lexer.commenters = True, "#"
    try:
        tokens = list(lexer)
    except ValueError:
        if strict:
            raise
        return ()
    segments: list[tuple[str, ...]] = []
    start = 0
    for index, token in enumerate((*tokens, ";")):
        if token not in _SHELL_SEPARATORS:
            continue
        segment = tuple(tokens[start:index])
        start = index + 1
        command = segment if preserve_context else _shell_segment_command(segment)
        if command:
            segments.append(command)
    return tuple(segments)


def _shell_segment_command(tokens: tuple[str, ...]) -> tuple[str, ...]:
    for index, argument in enumerate(tokens):
        if argument == "env":
            command_index = env_command_start(tokens, index + 1)
            return tokens[command_index:] if command_index < len(tokens) else ()
        if _ignored_shell_token(argument):
            continue
        if argument in _SHELL_NON_EXECUTABLES or argument.startswith("$"):
            return ()
        return tokens[index:]
    return ()


def command_tokens(tokens: tuple[str, ...]) -> tuple[str, ...]:
    index = 0
    while index < len(tokens):
        argument = tokens[index]
        if argument == "env":
            index = env_command_start(tokens, index + 1)
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


def env_command_start(tokens: tuple[str | None, ...], index: int) -> int:
    while index < len(tokens):
        argument = tokens[index]
        if argument is None:
            return index
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


def _ignored_shell_token(token: str) -> bool:
    return bool(
        _SHELL_ASSIGNMENT.fullmatch(token)
        or token.startswith("-")
        or token.isdigit()
        or token in _SHELL_PREFIXES
    )


_SHELL_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=.*")

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

_ENV_OPTIONS_WITH_VALUE = frozenset({"--chdir", "--unset", "-C", "-u"})
