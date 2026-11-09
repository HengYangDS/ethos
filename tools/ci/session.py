"""The part of a Nox session that the repository's sessions use, typed by its structure."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal
from typing import NoReturn
from typing import Protocol
from typing import overload

if TYPE_CHECKING:
    import os
    from collections.abc import Mapping

    import nox


class Session(Protocol):
    """What a session body may ask of Nox; `nox.Session` satisfies it without declaring it."""

    @property
    def posargs(self) -> list[str]: ...

    @overload
    def run(
        self,
        *args: str | os.PathLike[str],
        env: Mapping[str, str | None] | None = None,
        silent: Literal[False] = ...,
    ) -> bool | None: ...

    @overload
    def run(
        self,
        *args: str | os.PathLike[str],
        env: Mapping[str, str | None] | None = None,
        silent: Literal[True],
    ) -> str | None: ...

    @overload
    def run(
        self,
        *args: str | os.PathLike[str],
        env: Mapping[str, str | None] | None = None,
        silent: bool,
    ) -> str | bool | None: ...

    def log(self, *args: object, **kwargs: object) -> None: ...

    def error(self, *args: object) -> NoReturn: ...


if TYPE_CHECKING:

    def _conforms(session: nox.Session) -> Session:
        """Nox registers sessions by name, so this binding is where ty checks conformance."""
        return session
