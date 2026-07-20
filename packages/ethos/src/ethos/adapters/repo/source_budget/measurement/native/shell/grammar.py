"""Finite grammar state and heredoc quote removal for the shell lexer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Never

__all__ = (
    "FunctionHeader",
    "balanced_closure",
    "consume_heredocs",
    "finish_shell_state",
    "heredoc_fragment",
    "is_redirect_operator",
    "track_case_operator",
    "track_shell_newline",
    "track_shell_word",
)

_CASE_SEPARATORS = {";;", ";&", ";;&"}
_CASE_TAIL_OPERATORS = {"&&", "||", ";", "&", "|", ")", "}", "]]"}
_COMMAND_WORDS = {"do", "elif", "else", "if", "then", "time", "until", "while"}
_REDIRECT_OPERATORS = {
    "&>",
    "&>>",
    ">",
    ">>",
    "<",
    "<<",
    "<<-",
    "<<<",
    "<&",
    ">&",
    "<>",
    ">|",
}
_FUNCTION_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_FUNCTION_RESERVED_WORDS = {
    "case",
    "coproc",
    "do",
    "done",
    "elif",
    "else",
    "esac",
    "fi",
    "for",
    "function",
    "if",
    "in",
    "select",
    "then",
    "time",
    "until",
    "while",
}
_FUNCTION_KEYWORD = "keyword"
_FUNCTION_NAME_CANDIDATE = "name"
_FUNCTION_PAREN = "paren"
_FUNCTION_BODY = "body"
_UNFINISHED_FUNCTION_PHASES = {_FUNCTION_KEYWORD, _FUNCTION_PAREN, _FUNCTION_BODY}


def _raise(message: str) -> Never:
    raise ValueError(message)


def _is_function_name(literal: str | None) -> bool:
    return bool(
        literal and literal not in _FUNCTION_RESERVED_WORDS and _FUNCTION_NAME.fullmatch(literal)
    )


def _literal_word(fragments: tuple[tuple[str, str], ...]) -> str | None:
    return fragments[0][1] if len(fragments) == 1 and fragments[0][0] == "WORD" else None


def _is_line_continuation(fragments: tuple[tuple[str, str], ...]) -> bool:
    return fragments == (("ESCAPED", "\\\n"),)


@dataclass(slots=True)
class FunctionHeader:
    """Track the finite Bash/Zsh function-definition header lifecycle."""

    enabled: bool = True
    phase: str = ""

    @property
    def unfinished(self) -> bool:
        """Return whether the current phase still requires syntax."""
        return self.phase in _UNFINISHED_FUNCTION_PHASES

    def track_word(
        self,
        fragments: tuple[tuple[str, str], ...],
        *,
        was_command_start: bool,
        command_start: bool,
    ) -> bool:
        """Advance the header after one complete shell word."""
        if _is_line_continuation(fragments):
            return command_start
        literal = _literal_word(fragments)
        if not self.enabled:
            self.phase = ""
            return command_start
        if self.phase == _FUNCTION_KEYWORD:
            if not _is_function_name(literal):
                _raise("shell function name is invalid")
            self.phase = _FUNCTION_BODY
            return True
        if self.phase in {_FUNCTION_PAREN, _FUNCTION_BODY}:
            _raise("shell function body is missing")
        if was_command_start and literal == "function":
            self.phase = _FUNCTION_KEYWORD
            return True
        self.phase = (
            _FUNCTION_NAME_CANDIDATE if was_command_start and _is_function_name(literal) else ""
        )
        return command_start

    def track_operator(self, operator: str, *, command_start: bool) -> bool:
        """Advance the header after one admitted shell operator."""
        if not self.enabled:
            self.phase = ""
            return command_start
        if self.phase == _FUNCTION_NAME_CANDIDATE:
            self.phase = _FUNCTION_PAREN if operator == "(" else ""
            return command_start
        if self.phase == _FUNCTION_KEYWORD:
            _raise("shell function name is missing")
        if self.phase == _FUNCTION_PAREN:
            if operator != ")":
                _raise("shell function signature is not empty")
            self.phase = _FUNCTION_BODY
            return True
        if self.phase == _FUNCTION_BODY:
            if operator == "{":
                self.phase = ""
                return command_start
            if operator == "(":
                self.phase = _FUNCTION_PAREN
                return command_start
            _raise("shell function body is missing")
        self.phase = ""
        return command_start

    def track_newline(self) -> None:
        """Advance the header across one physical line boundary."""
        if not self.enabled:
            self.phase = ""
        elif self.phase in {_FUNCTION_KEYWORD, _FUNCTION_PAREN}:
            _raise("shell function header is incomplete")
        elif self.phase != _FUNCTION_BODY:
            self.phase = ""


def finish_shell_state(
    heredoc_operator: str | None,
    pending: list[tuple[str, bool]],
    groups: list[str],
    cases: list[tuple[str, int]],
    function_header: FunctionHeader,
) -> None:
    """Reject any unfinished top-level shell grammar state."""
    if cases and cases[-1][0] == "closed":
        cases.pop()
    if heredoc_operator is not None or pending or groups or cases or function_header.unfinished:
        _raise("shell structure is unterminated")


def balanced_closure(
    groups: list[str],
    heredoc_operator: str | None,
    pending: list[tuple[str, bool]],
    cases: list[tuple[str, int]],
    function_header: FunctionHeader,
) -> bool:
    """Return whether a nested substitution is complete or reject invalid state."""
    if groups:
        return False
    if heredoc_operator is not None or pending or cases or function_header.unfinished:
        _raise("shell structure is unterminated")
    return True


def consume_heredocs(
    text: str,
    index: int,
    pending: list[tuple[str, bool]],
    tokens: list[tuple[str, str]],
) -> int:
    """Consume queued heredoc bodies in declaration order."""
    for delimiter, strip_tabs in pending:
        body_start = index
        while True:
            end = text.find("\n", index)
            line_end = len(text) if end < 0 else end
            compared = text[index:line_end]
            compared = compared.lstrip("\t") if strip_tabs else compared
            if compared == delimiter:
                tokens.append(("HEREDOC", text[body_start:index]))
                tokens.append(("HEREDOC_END", delimiter))
                index = line_end + (end >= 0)
                break
            if end < 0:
                _raise("shell heredoc is unterminated")
            index = end + 1
    return index


def is_redirect_operator(operator: str | None) -> bool:
    """Return whether an operator is an admitted redirection."""
    return operator in _REDIRECT_OPERATORS


def _track_closed_operator(operator: str, cases: list[tuple[str, int]]) -> bool | None:
    phase = cases[-1][0] if cases else ""
    if phase == "closed_redirect":
        _raise("shell case redirection target is missing")
    if phase != "closed":
        return None
    if is_redirect_operator(operator):
        cases[-1] = ("closed_redirect", cases[-1][1])
        return False
    parent_body = len(cases) > 1 and cases[-2][0] == "body"
    if operator in _CASE_SEPARATORS and not parent_body:
        _raise("shell case closure separator is invalid")
    if operator not in _CASE_TAIL_OPERATORS and operator not in _CASE_SEPARATORS:
        _raise("shell case closure tail is invalid")
    cases.pop()
    return None


def _track_pattern_operator(
    operator: str,
    cases: list[tuple[str, int]],
    group_depth: int,
    *,
    command_start: bool,
    minimum_depth: int,
) -> bool | None:
    phase = cases[-1][0] if cases else ""
    pattern_depth = max(minimum_depth, cases[-1][1]) if phase.startswith("pattern") else None
    if operator == "(" and phase == "pattern" and command_start and group_depth == pattern_depth:
        cases[-1] = ("pattern_open", cases[-1][1])
        return False
    if pattern_depth is None or group_depth != pattern_depth:
        return None
    if operator == ")":
        if phase != "pattern_value":
            _raise("shell case pattern is empty")
        cases[-1] = ("body", cases[-1][1])
        return True
    if operator == "|":
        if phase != "pattern_value":
            _raise("shell case pattern alternative is empty")
        cases[-1] = ("pattern_alt", cases[-1][1])
        return False
    return None


def track_case_operator(
    operator: str,
    cases: list[tuple[str, int]],
    group_depth: int,
    *,
    command_start: bool,
    minimum_depth: int,
) -> bool | None:
    """Handle a case-specific operator, or defer ordinary group tracking."""
    if (handled := _track_closed_operator(operator, cases)) is not None:
        return handled
    if (
        handled := _track_pattern_operator(
            operator,
            cases,
            group_depth,
            command_start=command_start,
            minimum_depth=minimum_depth,
        )
    ) is not None:
        return handled
    if cases and cases[-1][0] == "body" and operator in _CASE_SEPARATORS:
        cases[-1] = ("pattern", cases[-1][1])
        return True
    return None


def _track_subject_word(
    phase: str,
    literal: str | None,
    cases: list[tuple[str, int]],
    group_depth: int,
) -> bool | None:
    if phase == "subject":
        if literal == "in":
            _raise("shell case subject is missing")
        cases[-1] = ("subject_done", group_depth)
        return False
    if phase == "subject_done":
        if literal != "in":
            _raise("shell case subject has multiple words")
        cases[-1] = ("pattern", group_depth)
        return True
    return None


def _track_pattern_word(
    phase: str,
    literal: str | None,
    cases: list[tuple[str, int]],
    group_depth: int,
    *,
    command_start: bool,
) -> bool | None:
    if phase == "closed_redirect":
        cases[-1] = ("closed", group_depth)
        return False
    if phase == "closed":
        _raise("shell case closure has an extra word")
    if phase in {"pattern", "pattern_open", "pattern_alt"}:
        if phase == "pattern" and command_start and literal == "esac":
            cases.pop()
            cases.append(("closed", group_depth))
            return False
        cases[-1] = ("pattern_value", group_depth)
        return False
    if phase == "pattern_value":
        _raise("shell case pattern has multiple words")
    if phase == "body" and command_start and literal == "esac":
        cases.pop()
        cases.append(("closed", group_depth))
        return False
    return None


def track_shell_word(
    fragments: tuple[tuple[str, str], ...],
    cases: list[tuple[str, int]] | None,
    group_depth: int,
    *,
    assignment: bool,
    command_start: bool,
) -> bool:
    """Advance case and command-word state after one complete shell word."""
    if _is_line_continuation(fragments):
        return command_start
    literal = _literal_word(fragments)
    if cases and group_depth == cases[-1][1]:
        phase = cases[-1][0]
        if (tracked := _track_subject_word(phase, literal, cases, group_depth)) is not None:
            return tracked
        if (
            tracked := _track_pattern_word(
                phase,
                literal,
                cases,
                group_depth,
                command_start=command_start,
            )
        ) is not None:
            return tracked
    if command_start and assignment:
        return True
    if (
        cases is not None
        and command_start
        and literal == "case"
        and (not cases or cases[-1][0] == "body")
    ):
        cases.append(("subject", group_depth))
        return False
    return command_start and literal in _COMMAND_WORDS


def track_shell_newline(cases: list[tuple[str, int]]) -> None:
    """Apply line-boundary constraints to active case syntax."""
    if not cases:
        return
    phase = cases[-1][0]
    if phase == "closed":
        cases.pop()
    elif phase in {
        "closed_redirect",
        "pattern_alt",
        "pattern_open",
        "pattern_value",
        "subject",
    }:
        _raise("shell case phase cannot cross a line boundary")


_ANSI_SIMPLE_ESCAPES = {
    "a": "\a",
    "b": "\b",
    "e": "\x1b",
    "E": "\x1b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "\\": "\\",
    "'": "'",
    '"': '"',
    "?": "?",
}


def heredoc_fragment(kind: str, value: str) -> str:
    """Apply delimiter-word quote removal without performing expansions."""
    if kind in {"ARITHMETIC", "PARAMETER", "SUBSTITUTION", "WORD"}:
        return value
    if kind == "ESCAPED":
        return "" if value == "\\\n" else value[1:]
    if kind == "ANSI_QUOTED":
        return _remove_ansi_c_escapes(value[2:-1])
    if kind == "QUOTED" and value.startswith("'"):
        return value[1:-1]
    if kind == "QUOTED" and value.startswith('"'):
        return _remove_double_quote_escapes(value[1:-1])
    if kind == "QUOTED" and value.startswith("`"):
        return value
    _raise("shell heredoc delimiter is invalid")


def _remove_ansi_c_escapes(value: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(value):
        if value[index] != "\\":
            output.append(value[index])
            index += 1
            continue
        if index + 1 >= len(value):
            _raise("shell ANSI-C escape is unterminated")
        decoded, index = _decode_ansi_escape(value, index)
        output.append(decoded)
    return "".join(output)


def _decode_ansi_escape(value: str, index: int) -> tuple[str, int]:
    escaped = value[index + 1]
    if escaped in _ANSI_SIMPLE_ESCAPES:
        return _ANSI_SIMPLE_ESCAPES[escaped], index + 2
    if escaped == "x":
        digits = _ansi_digits(value, index + 2, "0123456789abcdefABCDEF", 2)
        return (chr(int(digits, 16)), index + 2 + len(digits)) if digits else ("\\x", index + 2)
    if escaped in "01234567":
        digits = escaped + _ansi_digits(value, index + 2, "01234567", 2)
        return chr(int(digits, 8)), index + 1 + len(digits)
    if escaped in {"u", "U"}:
        width = 4 if escaped == "u" else 8
        digits = _ansi_digits(value, index + 2, "0123456789abcdefABCDEF", width)
        if not digits:
            _raise("shell ANSI-C Unicode escape is invalid")
        return chr(int(digits, 16)), index + 2 + len(digits)
    if escaped == "c":
        if index + 2 >= len(value):
            _raise("shell ANSI-C control escape is invalid")
        control = value[index + 2]
        return chr(0x7F if control == "?" else ord(control.upper()) & 0x1F), index + 3
    return f"\\{escaped}", index + 2


def _ansi_digits(value: str, index: int, allowed: str, limit: int) -> str:
    end = index
    while end < len(value) and end - index < limit and value[end] in allowed:
        end += 1
    return value[index:end]


def _remove_double_quote_escapes(value: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value) and value[index + 1] in '$`"\\\n':
            index += 1
            if value[index] != "\n":
                output.append(value[index])
        else:
            output.append(value[index])
        index += 1
    return "".join(output)
