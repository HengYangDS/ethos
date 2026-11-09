"""A typed Nox session double for the repository's own sessions."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal
from typing import NoReturn
from typing import overload

import pytest

if TYPE_CHECKING:
    import os
    from collections.abc import Callable
    from collections.abc import Mapping
    from collections.abc import Sequence

type Environment = Mapping[str, str | None] | None
type Runner = Callable[[tuple[str, ...], Environment], object]


class SessionDouble:
    """Record each run and log, answer runs through `runner`, and fail the test on `error`."""

    def __init__(self, runner: Runner | None = None, *, posargs: Sequence[str] = ()) -> None:
        self._runner = runner
        self._posargs = [*posargs]
        self.runs: list[tuple[str, ...]] = []
        self.logs: list[tuple[object, ...]] = []

    @property
    def posargs(self) -> list[str]:
        return [*self._posargs]

    @overload
    def run(
        self, *args: str | os.PathLike[str], env: Environment = None, silent: Literal[False] = ...
    ) -> bool | None: ...

    @overload
    def run(
        self, *args: str | os.PathLike[str], env: Environment = None, silent: Literal[True]
    ) -> str | None: ...

    @overload
    def run(
        self, *args: str | os.PathLike[str], env: Environment = None, silent: bool
    ) -> str | bool | None: ...

    def run(
        self, *args: str | os.PathLike[str], env: Environment = None, silent: bool = False
    ) -> str | bool | None:
        """Answer a silent run with the runner's text, as Nox returns captured output."""
        command = tuple(str(argument) for argument in args)
        self.runs.append(command)
        answer = self._runner(command, env) if self._runner is not None else None
        if silent:
            return answer if isinstance(answer, str) else ""
        return None

    def log(self, *args: object, **kwargs: object) -> None:
        del kwargs
        self.logs.append(args)

    def error(self, *args: object) -> NoReturn:
        pytest.fail(" ".join(str(argument) for argument in args))
