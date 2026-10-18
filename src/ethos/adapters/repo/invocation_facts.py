"""Observe facts that cannot change within one application invocation only once.

An object named by its full object ID never changes, so within one invocation a repeated read
returns the first successful result instead of starting Git again. Refs, abbreviated names, the
index, the worktree and configuration-dependent output stay fresh observations. Failures are
never reused, because an object that is missing now may arrive later in the same invocation.
The build of the running product is likewise fixed once its code is executing.
"""

from __future__ import annotations

import re
import subprocess
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from dataclasses import field
from threading import Lock
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator
    from collections.abc import Mapping
    from pathlib import Path

IMMUTABLE_READ_BYTES = 64 << 20
_OBJECT = r"(?:[0-9a-f]{40}|[0-9a-f]{64})(?:\^\{(?:tree|commit|blob|tag)?\}|[~^][0-9]*)*"
_NAME = re.compile(_OBJECT + r"(?::.*)?", re.DOTALL)
_ENTRY = re.compile(_OBJECT + r":.*", re.DOTALL)
# Each plumbing read with the options whose output depends only on the named objects.
_OPTIONS = {
    "cat-file": frozenset({"-e", "-t", "-s", "-p"}),
    "ls-tree": frozenset({"-r", "-t", "-d", "-z", "--name-only", "--full-tree"}),
    "merge-base": frozenset({"--is-ancestor", "--all"}),
    "rev-parse": frozenset({"--verify", "--quiet", "-q"}),
    "show": frozenset(),
}


@dataclass
class _Invocation:
    lock: Lock = field(default_factory=Lock)
    reads: dict[tuple[object, ...], subprocess.CompletedProcess[Any]] = field(default_factory=dict)
    retained: int = 0
    facts: dict[tuple[object, ...], object] = field(default_factory=dict)


_SCOPE: ContextVar[_Invocation | None] = ContextVar("invocation_facts", default=None)


@contextmanager
def invocation_scope() -> Generator[None]:
    """Keep invocation facts until the outermost scope of this invocation ends."""
    if _SCOPE.get() is not None:
        yield
        return
    token = _SCOPE.set(_Invocation())
    try:
        yield
    finally:
        _SCOPE.reset(token)


def invocation_fact[T](key: tuple[object, ...], observe: Callable[[], T]) -> T:
    """Observe one invocation constant once per invocation; outside one, always observe."""
    scope = _SCOPE.get()
    if scope is None:
        return observe()
    with scope.lock:
        if key in scope.facts:
            return cast("T", scope.facts[key])
    value = observe()
    with scope.lock:
        return cast("T", scope.facts.setdefault(key, value))


def reuse_key(
    root: Path,
    args: tuple[str, ...],
    *,
    text: bool,
    observation: bool,
    config: Mapping[str, str],
) -> tuple[object, ...] | None:
    """Name a reusable read, or None when its output can change within the invocation."""
    if _SCOPE.get() is None or not args or (allowed := _OPTIONS.get(args[0])) is None:
        return None
    operands = [argument for argument in args[1:] if argument not in allowed]
    pattern = _ENTRY if args[0] == "show" else _NAME
    if not operands or not all(pattern.fullmatch(operand) for operand in operands):
        return None
    return (str(root.resolve()), args, text, observation, tuple(sorted(config.items())))


def reused(key: tuple[object, ...] | None) -> subprocess.CompletedProcess[Any] | None:
    """Return a private copy of an earlier successful read."""
    scope = _SCOPE.get()
    if scope is None or key is None:
        return None
    with scope.lock:
        result = scope.reads.get(key)
    return None if result is None else _copy(result)


def retain(key: tuple[object, ...] | None, result: subprocess.CompletedProcess[Any]) -> None:
    """Keep a successful read for this invocation while it fits the retained-output budget."""
    scope = _SCOPE.get()
    if scope is None or key is None or result.returncode != 0:
        return
    size = len(result.stdout or "") + len(result.stderr or "")
    with scope.lock:
        if key not in scope.reads and scope.retained + size <= IMMUTABLE_READ_BYTES:
            scope.reads[key] = _copy(result)
            scope.retained += size


def _copy(result: subprocess.CompletedProcess[Any]) -> subprocess.CompletedProcess[Any]:
    return subprocess.CompletedProcess(result.args, result.returncode, result.stdout, result.stderr)
