"""Bind native producer capture to the exact pytest session and Ruff launch."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.domain.quality.nox as native_nox
import ethos.surface.pytest.plugin as pytest_plugin
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.materialization.input_resolution import runtime_wheel
from ethos.adapters.repo.runtime.selection import current_runtime
from tests.support.native_quality import native_quality_gate

if TYPE_CHECKING:
    from tests.unit.adoption.quality.native.conftest import NativeNoxSupply


@pytest.fixture
def observer_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Provide a declared unit producer identity; installed provenance is qualified separately."""
    wheel = tmp_path / "ethos-unit-observer.whl"
    wheel.write_bytes(b"unit producer identity")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    record: dict[str, object] = {
        "executable": sys.executable,
        "version": list(sys.version_info[:3]),
        "prefix": sys.prefix,
        "observer": {
            "requirement": f"ethos @ {wheel.as_uri()}#sha256={digest}",
            "runtime_digest": hashlib.sha256(b"unit runtime identity").hexdigest(),
            "wheel_sha256": digest,
        },
    }
    monkeypatch.setattr(native_nox, "runtime_identity", lambda: dict(record))
    monkeypatch.setattr(pytest_plugin, "runtime_identity", lambda: dict(record))
    return record


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


def test_pytest_plugin_binds_the_runtime_to_its_effective_configuration(
    tmp_path: Path, observer_runtime: dict[str, object]
) -> None:
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
    partial = json.loads(output.read_text(encoding="utf-8"))
    assert partial["observer"] == observer_runtime["observer"]
    assert partial["pytest"]["exitstatus"] is None
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
    tmp_path: Path, code: int, observer_runtime: dict[str, object]
) -> None:
    """The session child names itself and its one checker launch, then returns that exit code."""
    script = f"import sys; print('checked'); print('noted', file=sys.stderr); sys.exit({code})"
    record, request = _child_request(tmp_path, sys.executable, "-c", script)
    assert native_nox.main(request) == code
    recorded = json.loads(record.read_text(encoding="utf-8"))
    assert recorded == {
        **observer_runtime,
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


def test_child_operation_runs_as_the_installed_module(
    tmp_path: Path, native_nox_supply: NativeNoxSupply
) -> None:
    """An isolated installed child records the attempt's selected immutable observer."""
    gate = native_quality_gate(tmp_path, native_nox_supply)
    root = tmp_path / "repo"
    selected = current_runtime(Path(git_common_dir(root)))
    wheel = runtime_wheel(selected)
    requirement = f"ethos @ {wheel.as_uri()}#sha256={selected.wheel_sha256}"
    child = tmp_path / "observer-child"
    run_command(
        root,
        (
            str(native_nox_supply.uv),
            "venv",
            "--no-python-downloads",
            "--python",
            sys.executable,
            str(child),
        ),
        timeout=15,
        check=True,
    )
    python = child / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run_command(
        root,
        (
            str(native_nox_supply.uv),
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--python",
            str(python),
            requirement,
        ),
        timeout=30,
        check=True,
    )
    record, request = _child_request(tmp_path, str(python), "-c", "print('checked')")
    completed = run_command(
        root,
        (str(python), "-B", "-I", "-m", "ethos.domain.quality.nox", *request),
        timeout=15,
        env={
            "ETHOS_NATIVE_OBSERVER_REQUIREMENT": requirement,
            "ETHOS_NATIVE_OBSERVER_RUNTIME_DIGEST": selected.digest,
        },
    )
    assert completed.returncode == 0, completed.stderr
    recorded = json.loads(record.read_text(encoding="utf-8"))
    assert recorded["prefix"] == str(child)
    assert recorded["observer"] == {
        "requirement": requirement,
        "runtime_digest": selected.digest,
        "wheel_sha256": selected.wheel_sha256,
    }
    assert recorded["ruff"]["launches"] == 1
    assert recorded["ruff"]["stdout"] == "checked\n"
    assert gate.native_outputs


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
    tmp_path: Path, capsys: pytest.CaptureFixture[str], observer_runtime: dict[str, object]
) -> None:
    """A checker or configuration that cannot be opened is a refusal, never a pass."""
    record, request = _child_request(tmp_path, str(tmp_path / "absent-ruff"), "check")
    assert native_nox.main(request) == 2
    partial = json.loads(record.read_text(encoding="utf-8"))
    assert partial["observer"] == observer_runtime["observer"]
    assert partial["ruff"]["completed"] is False
    assert "absent-ruff" in capsys.readouterr().err
    record.unlink()
    (tmp_path / "ruff.toml").unlink()
    assert native_nox.main(request) == 2
    assert not record.exists()


def test_child_operation_refuses_missing_observer_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No native observer provenance means no checker launch or accepted record."""
    monkeypatch.delenv("ETHOS_NATIVE_OBSERVER_REQUIREMENT", raising=False)
    launched = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **_kwargs: launched.append(args))
    record, request = _child_request(tmp_path, "ruff", "check")
    assert native_nox.main(request) == 2
    assert not launched
    assert not record.exists()
    assert "python_native_observer_requirement_missing" in capsys.readouterr().err
