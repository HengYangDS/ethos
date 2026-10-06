"""Immutable declared-command identities for reference observation."""

from __future__ import annotations

import shlex
from dataclasses import dataclass


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
