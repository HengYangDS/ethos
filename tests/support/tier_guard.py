"""Report what each test case crosses: files, processes, databases and sockets (PEP 578).

The guard only reports; `test-tiers` arms it. While a case's setup, call and teardown run, one
audit hook per process records the crossing events below. Module loading, the test tools' own work
(pytest, Hypothesis, coverage, Allure, xdist), the run's report root and the setup of fixtures
wider than function scope are not the case's crossings; a wider fixture's finalizers still run
inside the last case's teardown. A case under `tests/unit` exceeds its tier on any crossing; any
other case only on a connection beyond loopback. Child processes, and reads a cached loader makes
for a later case, are outside its view.
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
    from types import FrameType

_EVENTS = frozenset(
    {
        "open",
        "os.listdir",
        "os.scandir",
        "os.remove",
        "os.rename",
        "subprocess.Popen",
        "os.system",
        "os.posix_spawn",
        "os.fork",
        "sqlite3.connect",
        "socket.connect",
    }
)
_PATH_EVENTS = frozenset({"open", "os.listdir", "os.scandir", "os.remove", "os.rename"})
# Module loading only: `importlib.metadata` and `importlib.resources` read files for their caller.
_LOADERS = ("_frozen_importlib", "importlib._bootstrap", "zipimport")
_TOOLS = frozenset(
    {
        "_pytest",
        "pluggy",
        "hypothesis",
        "_hypothesis_pytestplugin",
        "coverage",
        "pytest_cov",
        "allure",
        "allure_commons",
        "allure_pytest",
        "xdist",
        "execnet",
        "pytest_timeout",
    }
)
_OUTPUT = os.environ.get("ETHOS_NATIVE_OUTPUT_DIR")
_OWNED = (str(Path(_OUTPUT).absolute()) + os.sep,) if _OUTPUT else ()
# The running case's crossings, each mapped to whether it left this host; empty between cases.
_CASES: list[dict[str, bool]] = []
# One entry per wider-scope fixture setup in progress; its work is not the running case's.
_SHARED: list[str] = []
_INSTALLED: set[str] = set()


def _loopback(address: object) -> bool:
    """Whether a socket address stays on this host; a Unix-domain path always does."""
    if not isinstance(address, tuple):
        return True
    try:
        return ipaddress.ip_address(str(address[0]).partition("%")[0]).is_loopback
    except ValueError:
        return address[0] == "localhost"


def _case_origin(frame: FrameType | None) -> bool:
    """Whether the first frame outside the standard library is the case's own code."""
    while frame is not None:
        name = frame.f_globals.get("__name__", "")
        if name.startswith(_LOADERS):
            return False
        if name.partition(".")[0] not in sys.stdlib_module_names:
            return name.partition(".")[0] not in _TOOLS
        frame = frame.f_back
    return False


def _audit(event: str, arguments: tuple[object, ...]) -> None:
    """Record one crossing of the running case, ignoring loading, the tools and the run's output."""
    if not _CASES or _SHARED or event not in _EVENTS:
        return
    frame = inspect.currentframe()
    if not _case_origin(frame.f_back if frame is not None else None):
        return
    path = arguments[0] if event in _PATH_EVENTS else None
    if isinstance(path, str | bytes | os.PathLike) and str(
        Path(os.fsdecode(path)).absolute()
    ).startswith(_OWNED):
        return
    remote = event == "socket.connect" and not _loopback(arguments[1])
    _CASES[-1][event] = _CASES[-1].get(event, False) or remote


@pytest.hookimpl(trylast=True)
def pytest_configure() -> None:
    """Install the process's one audit hook; Python never removes an audit hook."""
    if "audit" not in _INSTALLED:
        sys.addaudithook(_audit)
        _INSTALLED.add("audit")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup() -> Generator[None, None, None]:
    """Start the case's record before any of its fixtures is set up."""
    _CASES.append({})
    return (yield)


@pytest.hookimpl(wrapper=True)
def pytest_fixture_setup(fixturedef: pytest.FixtureDef[object]) -> Generator[None, object, object]:
    """Leave a wider-scope fixture's setup out of the case that happens to request it first."""
    if fixturedef.scope == "function":
        return (yield)
    _SHARED.append(fixturedef.argname)
    try:
        return (yield)
    finally:
        _SHARED.pop()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item: pytest.Item) -> Generator[None, None, None]:
    """Attach the case's crossings and whether they exceed its tier to its properties."""
    try:
        return (yield)
    finally:
        crossed = _CASES.pop() if _CASES else {}
        if crossed:
            unit = Path(item.path).is_relative_to(Path(item.config.rootpath) / "tests/unit")
            exceeds = unit or any(crossed.values())
            item.user_properties.append(("ethos.crossed", ",".join(sorted(crossed))))
            item.user_properties.append(("ethos.exceeds", str(exceeds).lower()))
