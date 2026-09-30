"""Argument-vector grammar preserves partial words and identity-relevant demand."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from typing import overload

from ethos.repository.policy.references.commands import syntax


@dataclass(frozen=True, slots=True)
class ArgumentVector:
    """Known positions plus an optional unknown-length suffix, not shell text."""

    words: tuple[str | None, ...]
    open_tail: bool = False


@overload
def python_module(
    tokens: tuple[str, ...], executable: str, *, open_tail: Literal[False] = False
) -> str: ...


@overload
def python_module(
    tokens: tuple[str | None, ...], executable: str, *, open_tail: bool = False
) -> str | None: ...


def python_module(
    tokens: tuple[str | None, ...], executable: str, *, open_tail: bool = False
) -> str | None:
    """Resolve interpreter module identity without demanding unrelated option values."""
    if not re.fullmatch(r"python(?:\d+(?:\.\d+)*)?", executable):
        return ""
    index = 1
    while index < len(tokens):
        option = tokens[index]
        if option is None:
            return None
        if option == "-m":
            return tokens[index + 1] if index + 1 < len(tokens) else None if open_tail else ""
        if option.startswith("-m"):
            return option[2:]
        if (
            not option.startswith("-")
            or option.startswith("-c")
            or option in {"--", "-h", "--help", "-V", "--version"}
        ):
            return ""
        index += 2 if option in {"-W", "-X", "--check-hash-based-pycs"} else 1
    return None if open_tail else ""


@overload
def child_tokens(
    tokens: tuple[str, ...], executable: str, *, open_tail: Literal[False] = False
) -> tuple[str, ...]: ...


@overload
def child_tokens(
    tokens: tuple[str | None, ...], executable: str, *, open_tail: bool = False
) -> tuple[str | None, ...] | None: ...


def child_tokens(
    tokens: tuple[str | None, ...], executable: str, *, open_tail: bool = False
) -> tuple[str | None, ...] | None:
    """Locate a launcher's child; unknown leaf arguments cannot create children."""
    if executable == "env":
        child = tokens[syntax.env_command_start(tokens, 1) :]
        return child if child or not open_tail else None
    if executable == "uv":
        return _uv_child(tokens, open_tail=open_tail)
    if executable in {"npx", "uvx"}:
        options = _NPX_OPTIONS_WITH_VALUE if executable == "npx" else _UVX_OPTIONS_WITH_VALUE
        child = _tokens_after_options(tokens[1:], options)
        if not child:
            return None if open_tail else ()
        if child[0] is None:
            return child
        return (_package_command(child[0]), *child[1:])
    return ()


def _uv_child(tokens: tuple[str | None, ...], *, open_tail: bool) -> tuple[str | None, ...] | None:
    args = _tokens_after_options(tokens[1:], _UV_RUN_OPTIONS_WITH_VALUE)
    if args and args[0] not in {"run", None}:
        return ()
    if not args or args[0] is None:
        return None if open_tail or args else ()
    child = _tokens_after_options(args[1:], _UV_RUN_OPTIONS_WITH_VALUE)
    return child if child or not open_tail else None


def _tokens_after_options[T: str | None](
    tokens: tuple[T, ...], options_with_value: frozenset[str]
) -> tuple[T, ...]:
    index = 0
    while index < len(tokens):
        argument = tokens[index]
        if argument is None:
            return tokens[index:]
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


def npm_script_name(tokens: tuple[str | None, ...], *, open_tail: bool = False) -> str | None:
    """Distinguish an absent npm script from an unresolved selection."""
    args = _tokens_after_options(tokens[1:], _NPM_OPTIONS_WITH_VALUE)
    if not args:
        return None if open_tail else ""
    if args[0] is None:
        return None
    if args[0] not in {"run", "run-script"}:
        return ""
    script = _tokens_after_options(args[1:], _NPM_OPTIONS_WITH_VALUE)
    return script[0] if script else None if open_tail else ""


def executable_identity(token: str) -> str:
    """Keep a native filename intact; whitespace and digits are not shell syntax."""
    if token.startswith("/dev/"):
        return ""
    if token.startswith("/"):
        token = token.rsplit("/", maxsplit=1)[-1]
    elif "/" in token:
        return ""
    return token if token and not any(character in token for character in "\n\r\0") else ""


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
