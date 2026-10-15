"""Bind native producer capture to the exact pytest session and Ruff launch."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.domain.quality.nox as native_nox
import ethos.surface.pytest.plugin as pytest_plugin


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


def _child_request(tmp_path: Path, *command: str) -> tuple[Path, list[str]]:
    """Return the record path and the installed operation's arguments for one checker argv."""
    configuration = tmp_path / "ruff.toml"
    configuration.write_text("", encoding="utf-8")
    record = tmp_path / "static-runtime.json"
    options = ("--runtime-output", str(record), "--session", "static-3.14")
    return record, ["run", *options, "--configuration", str(configuration), "--", *command]


@pytest.mark.parametrize("code", [0, 3])
def test_child_operation_records_its_interpreter_with_the_single_launch(
    tmp_path: Path, code: int
) -> None:
    """The session child names itself and its one checker launch, then returns that exit code."""
    script = f"import sys; print('checked'); print('noted', file=sys.stderr); sys.exit({code})"
    record, request = _child_request(tmp_path, sys.executable, "-c", script)
    assert native_nox.main(request) == code
    recorded = json.loads(record.read_text(encoding="utf-8"))
    assert recorded == {
        "executable": sys.executable,
        "version": list(sys.version_info[:3]),
        "prefix": sys.prefix,
        "ruff": {
            "session": "static-3.14",
            "executable": sys.executable,
            "argv": [sys.executable, "-c", script],
            "cwd": str(Path.cwd().resolve()),
            "configuration": str((tmp_path / "ruff.toml").resolve()),
            "configuration_sha256": hashlib.sha256(b"").hexdigest(),
            "completed": code == 0,
            "launches": 1,
            "stdout": "checked\n",
            "stderr": "noted\n",
        },
    }


def test_child_operation_runs_as_the_installed_module(tmp_path: Path) -> None:
    """An isolated interpreter reaches the operation through its module name alone."""
    record, request = _child_request(tmp_path, sys.executable, "-c", "print('checked')")
    module = (sys.executable, "-B", "-I", "-m", "ethos.domain.quality.nox")
    completed = subprocess.run((*module, *request), capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    recorded = json.loads(record.read_text(encoding="utf-8"))
    assert (recorded["prefix"], recorded["ruff"]["launches"]) == (sys.prefix, 1)
    assert recorded["ruff"]["stdout"] == "checked\n"


def test_child_operation_refuses_a_request_without_one_exact_command(tmp_path: Path) -> None:
    """Absent options, a missing separator and an empty checker argv launch nothing."""
    record, request = _child_request(tmp_path)
    without_separator = request[:-1]
    without_output = [request[0], *request[3:], "ruff"]
    for incomplete in (request, without_separator, without_output):
        with pytest.raises(SystemExit) as refusal:
            native_nox.main(incomplete)
        assert refusal.value.code == 2
    assert not record.exists()


def test_child_operation_reports_an_unlaunchable_checker_as_incomplete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A checker or configuration that cannot be opened is a refusal, never a pass."""
    record, request = _child_request(tmp_path, str(tmp_path / "absent-ruff"), "check")
    assert native_nox.main(request) == 2
    assert json.loads(record.read_text(encoding="utf-8"))["ruff"]["completed"] is False
    assert "absent-ruff" in capsys.readouterr().err
    record.unlink()
    (tmp_path / "ruff.toml").unlink()
    assert native_nox.main(request) == 2
    assert not record.exists()
