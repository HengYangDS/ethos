"""Report what each test case crosses: files, processes, databases and sockets (PEP 578).

The guard only reports; `test-tiers` arms it. While a case's call runs, one audit hook per process
records the crossing events below. Module loading and the run's own report and Hypothesis roots are
not crossings. A case under `tests/unit` exceeds its tier on any crossing; any other case only on a
connection beyond loopback. Child processes, and reads a cached loader makes for a later case, are
outside its view.
"""

from __future__ import annotations

import inspect
import ipaddress
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

_EVENTS = frozenset(
    {"open", "os.listdir", "os.scandir", "subprocess.Popen", "sqlite3.connect", "socket.connect"}
)
_PATH_EVENTS = frozenset({"open", "os.listdir", "os.scandir"})
_LOADERS = ("_frozen_importlib", "importlib")
_OWNED = tuple(
    str(Path(root).absolute()) + os.sep
    for root in (
        os.environ.get("ETHOS_NATIVE_OUTPUT_DIR"),
        str(Path(__file__).resolve().parents[2] / "build/runtime/tool-cache/hypothesis"),
    )
    if root
)
# The running call's crossings, each mapped to whether it left this host; empty between calls.
_CALLS: list[dict[str, bool]] = []
_INSTALLED: set[str] = set()


def _loopback(address: object) -> bool:
    """Whether a socket address stays on this host; a Unix-domain path always does."""
    if not isinstance(address, tuple):
        return True
    try:
        return ipaddress.ip_address(str(address[0]).partition("%")[0]).is_loopback
    except ValueError:
        return address[0] == "localhost"


def _audit(event: str, arguments: tuple[object, ...]) -> None:
    """Record one crossing of the running call, ignoring module loading and the run's own output."""
    if not _CALLS or event not in _EVENTS:
        return
    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    if caller is not None and caller.f_globals.get("__name__", "").startswith(_LOADERS):
        return
    path = arguments[0] if event in _PATH_EVENTS else None
    if isinstance(path, str | bytes | os.PathLike) and str(
        Path(os.fsdecode(path)).absolute()
    ).startswith(_OWNED):
        return
    remote = event == "socket.connect" and not _loopback(arguments[1])
    _CALLS[-1][event] = _CALLS[-1].get(event, False) or remote


@pytest.hookimpl(trylast=True)
def pytest_configure() -> None:
    """Install the process's one audit hook; Python never removes an audit hook."""
    if "audit" not in _INSTALLED:
        sys.addaudithook(_audit)
        _INSTALLED.add("audit")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, None, None]:
    """Attach the call's crossings and whether they exceed its tier to the case's properties."""
    _CALLS.append({})
    try:
        return (yield)
    finally:
        crossed = _CALLS.pop()
        if crossed:
            unit = Path(item.path).is_relative_to(Path(item.config.rootpath) / "tests/unit")
            exceeds = unit or any(crossed.values())
            item.user_properties.append(("ethos.crossed", ",".join(sorted(crossed))))
            item.user_properties.append(("ethos.exceeds", str(exceeds).lower()))
