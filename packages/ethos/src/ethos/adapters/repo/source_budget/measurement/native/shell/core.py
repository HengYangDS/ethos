"""Finite repository-owned Bash and Zsh lexical measurement grammar."""

from __future__ import annotations

import re
from typing import Never

import ethos.adapters.repo.source_budget.measurement.native.shell.grammar as shell_grammar

__all__: tuple[str, ...] = ()

_SHELL_OPERATOR_TEXT = (
    ";;& &>> <<< <<- && || ;; ;& |& &> >> << <& >& <> >| [[ ]] (( )) ; & | ( ) { } < >"
)
_SHELL_OPERATORS = tuple(sorted(_SHELL_OPERATOR_TEXT.split(), key=lambda item: (-len(item), item)))
_WORD_BREAK_OPERATORS = tuple(
    item for item in _SHELL_OPERATORS if item not in {"[[", "]]", "{", "}"}
)
_SHELL_GROUPS = {"(": ")", "[[": "]]", "((": "))", "{": "}"}
_SHELL_CLOSERS = tuple(_SHELL_GROUPS.values())
_COMMAND_OPERATORS = {";", "&&", "||", "|", "&", "(", "{"}
_NON_REDIRECT_GROUPS = {"))", "]]"}
_WORD_VARIABLE = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*|\$[0-9@*#?$!_-]")
_ASSIGNMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _raise(error_type: type[Exception], message: str) -> Never:
    raise error_type(message)


def shell_tokens(text: str) -> tuple[tuple[str, str], ...]:
    """Tokenize one admitted Bash or Zsh carrier with finite grammar state."""
    tokens: list[tuple[str, str]] = []
    pending: list[tuple[str, bool]] = []
    groups: list[str] = []
    cases: list[tuple[str, int]] = []
    index, command_start = 0, True
    heredoc_operator: str | None = None
    function_header = shell_grammar.FunctionHeader()
    while index < len(text):
        char = text[index]
        if char == "\n":
            shell_grammar.track_shell_newline(cases)
            function_header.track_newline()
            index = _consume_balanced_newline(
                text,
                index,
                pending,
                tokens,
                heredoc_operator=heredoc_operator,
            )
            command_start = True
            continue
        if char.isspace():
            index += 1
            continue
        if heredoc_operator is not None:
            fragments, delimiter, index = _read_heredoc_word(text, index)
            tokens.extend(fragments)
            pending.append((delimiter, heredoc_operator == "<<-"))
            heredoc_operator = None
            if cases and cases[-1][0] == "closed_redirect":
                cases[-1] = ("closed", cases[-1][1])
            else:
                command_start = False
            continue
        if char == "#":
            end = text.find("\n", index)
            end = len(text) if end < 0 else end
            tokens.append(("COMMENT", text[index:end]))
            index = end
            continue
        operator = _shell_operator(text, index, groups, command_start=command_start)
        if operator is not None and not text.startswith(("<(", ">("), index):
            next_command_start = _track_shell_operator(
                operator,
                groups,
                cases,
                command_start=command_start,
                minimum_depth=0,
            )
            command_start = function_header.track_operator(
                operator,
                command_start=next_command_start,
            )
            tokens.append(("OP", operator))
            heredoc_operator = (
                operator
                if operator in {"<<", "<<-"} and not _inside_non_redirect_group(groups)
                else heredoc_operator
            )
            index += len(operator)
            continue
        fragments, index, assignment = _shell_word(
            text,
            index,
            allow_array_assignment=command_start,
        )
        tokens.extend(fragments)
        was_command_start = command_start
        if not _case_io_number_prefix(fragments, cases, text, index, groups):
            command_start = shell_grammar.track_shell_word(
                fragments,
                cases,
                len(groups),
                assignment=assignment,
                command_start=command_start,
            )
        command_start = function_header.track_word(
            fragments,
            was_command_start=was_command_start,
            command_start=command_start,
        )
    shell_grammar.finish_shell_state(heredoc_operator, pending, groups, cases, function_header)
    return tuple(tokens)


def _track_shell_group(operator: str, groups: list[str]) -> None:
    if closer := _SHELL_GROUPS.get(operator):
        groups.append(closer)
    elif operator in _SHELL_GROUPS.values() and (not groups or groups.pop() != operator):
        _raise(ValueError, "shell group is unmatched")


def _track_shell_operator(
    operator: str,
    groups: list[str],
    cases: list[tuple[str, int]],
    *,
    command_start: bool,
    minimum_depth: int,
) -> bool:
    handled = shell_grammar.track_case_operator(
        operator,
        cases,
        len(groups),
        command_start=command_start,
        minimum_depth=minimum_depth,
    )
    if handled is not None:
        return handled
    _track_shell_group(operator, groups)
    return operator in _COMMAND_OPERATORS


def _shell_word(
    text: str,
    index: int,
    *,
    allow_array_assignment: bool,
    break_operators: bool = True,
    stop: str | None = None,
) -> tuple[tuple[tuple[str, str], ...], int, bool]:
    fragments: list[tuple[str, str]] = []
    assignment_end = _assignment_prefix_end(text, index) if allow_array_assignment else None
    while index < len(text) and not text[index].isspace():
        if fragments and (
            (stop is not None and text.startswith(stop, index))
            or (
                break_operators
                and _word_operator(text, index) is not None
                and not text.startswith(("<(", ">("), index)
            )
        ):
            break
        kind, value, end = _shell_atom(
            text,
            index,
            assignment_end=assignment_end if not fragments else None,
            break_operators=break_operators,
            stop=stop,
        )
        if end <= index:
            _raise(ValueError, "shell lexer made no progress")
        fragments.append((kind, value))
        index = end
        if len(fragments) == 1 and (kind, value) == ("ESCAPED", "\\\n"):
            break
    if not fragments:
        _raise(ValueError, "shell word is empty")
    return tuple(fragments), index, assignment_end is not None


def _shell_atom(
    text: str,
    index: int,
    *,
    assignment_end: int | None = None,
    break_operators: bool = True,
    stop: str | None = None,
) -> tuple[str, str, int]:
    if prefixed := _shell_prefixed_atom(text, index):
        return prefixed
    end = index if assignment_end is None else assignment_end
    while end < len(text):
        char = text[end]
        if char.isspace() or char in "'\"`\\$":
            break
        if (stop is not None and text.startswith(stop, end)) or (
            break_operators and _word_operator(text, end)
        ):
            break
        end += 1
    return "WORD", text[index:end], end


def _assignment_prefix_end(text: str, index: int) -> int | None:
    name = _ASSIGNMENT_NAME.match(text, index)
    if name is None:
        return None
    cursor = name.end()
    return _assignment_operator_end(text, cursor) or _array_assignment_end(text, cursor)


def _assignment_operator_end(text: str, cursor: int) -> int | None:
    if text[cursor : cursor + 2] == "+=":
        return cursor + 2
    if text[cursor : cursor + 1] == "=":
        return cursor + 1
    return None


def _array_assignment_end(text: str, cursor: int) -> int | None:
    if cursor >= len(text) or text[cursor] != "[":
        return None
    depth = 1
    cursor += 1
    while cursor < len(text):
        if text[cursor] == "\\":
            cursor += 2
            continue
        if prefixed := _shell_prefixed_atom(text, cursor):
            cursor = prefixed[2]
            continue
        if text[cursor] == "[":
            depth += 1
        elif text[cursor] == "]":
            depth -= 1
            if depth == 0:
                return _assignment_operator_end(text, cursor + 1)
        cursor += 1
    return None


def _word_operator(text: str, index: int) -> str | None:
    return next((item for item in _WORD_BREAK_OPERATORS if text.startswith(item, index)), None)


def _case_io_number_prefix(
    fragments: tuple[tuple[str, str], ...],
    cases: list[tuple[str, int]],
    text: str,
    index: int,
    groups: list[str],
) -> bool:
    return (
        bool(cases)
        and cases[-1][0] == "closed"
        and len(fragments) == 1
        and fragments[0][0] == "WORD"
        and fragments[0][1].isdigit()
        and shell_grammar.is_redirect_operator(
            _shell_operator(text, index, groups, command_start=False)
        )
    )


def _shell_prefixed_atom(text: str, index: int) -> tuple[str, str, int] | None:
    if text.startswith(("$((", "$(", "${", "<(", ">("), index):
        kind = "ARITHMETIC" if text.startswith("$((", index) else "SUBSTITUTION"
        end = _balanced_end(text, index + 1)
        return kind, text[index:end], end
    if text.startswith("$'", index):
        end = _quoted_end(text, index + 1, "'")
        return "ANSI_QUOTED", text[index:end], end
    if text[index] in {"'", '"', "`"}:
        end = _quoted_end(text, index, text[index])
        return "QUOTED", text[index:end], end
    if text[index] == "\\":
        if index + 1 >= len(text):
            _raise(ValueError, "shell escape is unterminated")
        return "ESCAPED", text[index : index + 2], index + 2
    if text[index] == "$":
        match = _WORD_VARIABLE.match(text, index)
        return (
            ("WORD", "$", index + 1)
            if match is None
            else (
                "PARAMETER",
                match.group(),
                match.end(),
            )
        )
    return None


def _quoted_end(text: str, index: int, quote: str) -> int:
    cursor = index + 1
    allows_escape = quote != "'" or text[index - 1 : index] == "$"
    while cursor < len(text):
        if text[cursor] == "\\" and allows_escape:
            cursor += 2
            continue
        if quote == '"' and text.startswith(("$(", "${"), cursor):
            cursor = _balanced_end(text, cursor + 1)
            continue
        if quote == '"' and text[cursor] == "`":
            cursor = _quoted_end(text, cursor, "`")
            continue
        if text[cursor] == quote:
            return cursor + 1
        cursor += 1
    _raise(ValueError, "shell quote is unterminated")


def _balanced_end(text: str, opener: int) -> int:
    if text[opener] == "{":
        return _parameter_expansion_end(text, opener)
    arithmetic = text[opener - 1 : opener + 2] == "$(("
    groups = ["))" if arithmetic else ")"]
    cases: list[tuple[str, int]] = []
    pending: list[tuple[str, bool]] = []
    ignored_tokens: list[tuple[str, str]] = []
    cursor = opener + (2 if arithmetic else 1)
    command_start = True
    heredoc_operator: str | None = None
    function_header = shell_grammar.FunctionHeader(enabled=not arithmetic)
    while cursor < len(text):
        if text[cursor] == "\n":
            shell_grammar.track_shell_newline(cases)
            function_header.track_newline()
            cursor = _consume_balanced_newline(
                text,
                cursor,
                pending,
                ignored_tokens,
                heredoc_operator=heredoc_operator,
            )
            command_start = True
            continue
        if (layout_end := _balanced_layout_end(text, cursor)) is not None:
            cursor = layout_end
            continue
        if heredoc_operator is not None:
            _fragments, delimiter, cursor = _read_heredoc_word(text, cursor)
            pending.append((delimiter, heredoc_operator == "<<-"))
            heredoc_operator = None
            if cases and cases[-1][0] == "closed_redirect":
                cases[-1] = ("closed", cases[-1][1])
            else:
                command_start = False
            continue
        operator = _shell_operator(text, cursor, groups, command_start=command_start)
        if operator is not None and not text.startswith(("<(", ">("), cursor):
            next_command_start = _track_shell_operator(
                operator,
                groups,
                cases,
                command_start=command_start,
                minimum_depth=1,
            )
            command_start = function_header.track_operator(
                operator,
                command_start=next_command_start,
            )
            heredoc_operator = (
                operator
                if operator in {"<<", "<<-"} and not _inside_non_redirect_group(groups)
                else heredoc_operator
            )
            cursor += len(operator)
            if shell_grammar.balanced_closure(
                groups,
                heredoc_operator,
                pending,
                cases,
                function_header,
            ):
                return cursor
            continue
        fragments, cursor, assignment = _shell_word(
            text,
            cursor,
            allow_array_assignment=(command_start and not arithmetic),
        )
        was_command_start = command_start
        if not _case_io_number_prefix(fragments, cases, text, cursor, groups):
            command_start = shell_grammar.track_shell_word(
                fragments,
                None if arithmetic else cases,
                len(groups),
                assignment=assignment,
                command_start=command_start,
            )
        command_start = function_header.track_word(
            fragments,
            was_command_start=was_command_start,
            command_start=command_start,
        )
    _raise(ValueError, "shell substitution is unterminated")


def _balanced_layout_end(text: str, cursor: int) -> int | None:
    if text[cursor].isspace():
        return cursor + 1
    if text[cursor] != "#":
        return None
    end = text.find("\n", cursor)
    return len(text) if end < 0 else end


def _parameter_expansion_end(text: str, opener: int) -> int:
    cursor = opener + 1
    while cursor < len(text):
        if text[cursor] == "}":
            return cursor + 1
        if text[cursor].isspace():
            cursor += 1
            continue
        start = cursor
        _fragments, cursor, _assignment = _shell_word(
            text,
            cursor,
            allow_array_assignment=False,
            break_operators=False,
            stop="}",
        )
        if cursor <= start:
            _raise(ValueError, "shell lexer made no progress")
    _raise(ValueError, "shell substitution is unterminated")


def _consume_balanced_newline(
    text: str,
    cursor: int,
    pending: list[tuple[str, bool]],
    tokens: list[tuple[str, str]],
    *,
    heredoc_operator: str | None,
) -> int:
    if heredoc_operator is not None:
        _raise(ValueError, "shell heredoc delimiter is missing")
    cursor += 1
    if pending:
        cursor = shell_grammar.consume_heredocs(text, cursor, pending, tokens)
        pending.clear()
    return cursor


def _shell_operator(
    text: str,
    index: int,
    groups: list[str],
    *,
    command_start: bool,
) -> str | None:
    operator = next(
        (item for item in _SHELL_OPERATORS if text.startswith(item, index)),
        None,
    )
    if operator in {"[[", "{"} and (
        not command_start or not _operator_word_boundary(text, index + len(operator))
    ):
        return None
    if operator == "}":
        if not _operator_word_boundary(text, index + 1):
            return None
        if not groups or groups[-1] != operator:
            return operator if command_start else None
    if operator == "]]" and (
        not groups
        or groups[-1] != operator
        or not _operator_word_boundary(text, index + len(operator))
    ):
        return None
    if operator == "<<-" and _inside_non_redirect_group(groups):
        return "<<"
    return operator


def _operator_word_boundary(text: str, index: int) -> bool:
    return index >= len(text) or text[index].isspace() or _word_operator(text, index) is not None


def _inside_non_redirect_group(groups: list[str]) -> bool:
    return any(group in _NON_REDIRECT_GROUPS for group in groups)


def _read_heredoc_word(
    text: str,
    index: int,
) -> tuple[tuple[tuple[str, str], ...], str, int]:
    fragments: list[tuple[str, str]] = []
    delimiter: list[str] = []
    if text[index] == "#":
        _raise(ValueError, "shell heredoc delimiter is missing")
    while index < len(text) and not text[index].isspace():
        if _shell_operator(
            text, index, [], command_start=False
        ) is not None and not text.startswith(("<(", ">("), index):
            break
        kind, value, end = _shell_atom(text, index)
        fragments.append((kind, value))
        delimiter.append(shell_grammar.heredoc_fragment(kind, value))
        index = end
    if not fragments:
        _raise(ValueError, "shell heredoc delimiter is invalid")
    return tuple(fragments), "".join(delimiter), index
