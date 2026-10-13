"""Bind native producer capture to the exact pytest session and Ruff launch."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.domain.quality.nox as native_nox
import ethos.surface.pytest.plugin as pytest_plugin

if TYPE_CHECKING:
    from pathlib import Path


def _pytest_session(tmp_path: Path, output: object, configuration: Path | None) -> SimpleNamespace:
    options = {"ethos_runtime_output": output, "ethos_native_session": "tests-3.14"}
    config = SimpleNamespace(
        getoption=options.__getitem__,
        inipath=configuration,
        invocation_params=SimpleNamespace(args=("-q",)),
        rootpath=tmp_path,
        getini=lambda _name: ["error"],
    )
    return SimpleNamespace(config=config)


def test_pytest_plugin_binds_the_runtime_to_its_effective_configuration(tmp_path: Path) -> None:
    """The plugin records one attempt identity and refuses unbound output or configuration."""
    added: list[str] = []
    group = SimpleNamespace(addoption=lambda name, **_options: added.append(name))
    pytest_plugin.pytest_addoption(SimpleNamespace(getgroup=lambda _name: group))
    assert added == ["--ethos-runtime-output", "--ethos-native-session"]
    configuration = tmp_path / "pytest.toml"
    configuration.write_text("[pytest]\n", encoding="utf-8")
    output = tmp_path / "runtime.json"
    session = _pytest_session(tmp_path, str(output), configuration)
    pytest_plugin.pytest_sessionstart(session)
    assert json.loads(output.read_text(encoding="utf-8"))["pytest"]["exitstatus"] is None
    pytest_plugin.pytest_sessionfinish(session, 1)
    recorded = json.loads(output.read_text(encoding="utf-8"))["pytest"]
    assert recorded["exitstatus"] == 1
    assert recorded["configuration_sha256"] == hashlib.sha256(b"[pytest]\n").hexdigest()
    with pytest.raises(TypeError, match=r"^python_native_pytest_output_unbound$"):
        pytest_plugin.pytest_sessionstart(_pytest_session(tmp_path, None, configuration))
    with pytest.raises(ValueError, match=r"^python_native_pytest_config_unbound$"):
        pytest_plugin.pytest_sessionstart(_pytest_session(tmp_path, str(output), None))


def test_ruff_launch_binds_one_textual_process_request(tmp_path: Path) -> None:
    """Only the single checker launch inside the wrapper is retained with its output."""
    configuration = tmp_path / "ruff.toml"
    configuration.write_text("", encoding="utf-8")
    runtime = tmp_path / "static-runtime.json"
    runtime.write_text("{}", encoding="utf-8")

    class Session:
        def run(self, *command: str, **options: object) -> bool:
            subprocess.run(command, stdout=options["stdout"], stderr=options["stderr"], check=True)
            return True

    command = (sys.executable, "-c", "print('checked')")
    bound = {"runtime_output": runtime, "identity": "static", "configuration": configuration}
    assert native_nox.run_ruff(Session(), command, **bound) is True
    recorded = json.loads(runtime.read_text(encoding="utf-8"))["ruff"]
    assert (recorded["launches"], recorded["completed"], recorded["stdout"]) == (
        1,
        True,
        "checked\n",
    )
    runtime.write_text("[]", encoding="utf-8")
    with pytest.raises(TypeError, match=r"^python_native_toolchain_unbound$"):
        native_nox.run_ruff(Session(), command, **bound)


@pytest.mark.parametrize(
    ("arguments", "textual"),
    [
        (("ruff", ["ruff", "check"], None, None), True),
        ((b"ruff", ["ruff"], None, None), False),
        (("ruff", "ruff check", None, None), False),
        (("ruff", ["ruff", b"check"], None, None), False),
        (("ruff", ["ruff"], b"/", None), False),
    ],
)
def test_popen_requests_are_retained_only_as_text(arguments: tuple, *, textual: bool) -> None:
    """A launch request is retained only when every identity part is text."""
    assert (native_nox.popen_request(arguments) is not None) is textual


def test_popen_request_resolves_its_working_directory(tmp_path: Path) -> None:
    """The retained request names the resolved directory the child starts in."""
    request = native_nox.popen_request(("ruff", ("ruff", "check"), str(tmp_path), None))
    assert request == ("ruff", ("ruff", "check"), str(tmp_path.resolve()))
