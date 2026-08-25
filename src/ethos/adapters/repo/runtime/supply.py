"""Explicit capability contracts for immutable hook-runtime construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Literal

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class LockedSourceSupply:
    """A lock-current checkout that can build and resolve production dependencies."""

    source: Path
    wheel: Path
    interpreter: Path
    mode: Literal["locked-source"] = "locked-source"


@dataclass(frozen=True, slots=True)
class ImmutablePackageSupply:
    """A source-independent package runtime with an owned interpreter closure."""

    source: Path
    wheel: Path
    interpreter: Path
    mode: Literal["immutable-package"] = "immutable-package"


def runtime_supply(
    *,
    mode: Literal["locked-source", "immutable-package"],
    source: Path,
    wheel: Path,
    interpreter: Path | None = None,
) -> LockedSourceSupply | ImmutablePackageSupply:
    """Construct one explicit runtime supply without inferring mode from paths."""
    if mode == "locked-source":
        if interpreter is None:
            message = "runtime_supply_interpreter_missing"
            raise ValueError(message)
        return LockedSourceSupply(
            source=source,
            wheel=wheel,
            interpreter=interpreter,
        )
    if mode == "immutable-package":
        if interpreter is None:
            message = "runtime_supply_interpreter_missing"
            raise ValueError(message)
        return ImmutablePackageSupply(
            source=source,
            wheel=wheel,
            interpreter=interpreter,
        )
    message = "runtime_supply_mode_invalid"
    raise ValueError(message)
