"""Capture the running pytest session through its supported hooks."""

from __future__ import annotations

import hashlib
import json
import sys
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Accept only explicit attempt-owned output and native producer identity."""
    group = parser.getgroup("ethos-native-evidence")
    group.addoption("--ethos-runtime-output", default=None)
    group.addoption("--ethos-native-session", default=None)


def _write(session: pytest.Session, exitstatus: int | None) -> None:
    config = session.config
    output = config.getoption("ethos_runtime_output")
    producer = config.getoption("ethos_native_session")
    if not isinstance(output, str) or not isinstance(producer, str):
        msg = "python_native_pytest_output_unbound"
        raise TypeError(msg)
    selected = config.inipath
    if selected is None:
        msg = "python_native_pytest_config_unbound"
        raise ValueError(msg)
    payload = {
        "executable": sys.executable,
        "version": list(sys.version_info[:3]),
        "prefix": sys.prefix,
        "pytest": {
            "session": producer,
            "argv": list(config.invocation_params.args),
            "root": str(config.rootpath),
            "configuration": str(selected),
            "configuration_sha256": hashlib.sha256(selected.read_bytes()).hexdigest(),
            "version": version("pytest"),
            "warnings": list(config.getini("filterwarnings")),
            "exitstatus": exitstatus,
        },
    }
    Path(output).write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def pytest_sessionstart(session: pytest.Session) -> None:
    """Retain partial identity even if the selected tests fail or are interrupted."""
    _write(session, None)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Bind terminal outcome to the same runtime and effective native configuration."""
    _write(session, int(exitstatus))
