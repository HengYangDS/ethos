"""Bind native observer supply to selected bytes, never the adopter parent."""

from __future__ import annotations

import hashlib
import inspect
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

import ethos.domain.quality.nox as custody
import ethos.domain.quality.observer as native_observer
from ethos.adapters.gates.native.attempt import native_attempt
from ethos.adapters.gates.native.attempt import retained_execution
from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.contracts.evidence.observer import ObserverIdentity
from ethos.contracts.gates import Gate
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.governed_repository import committed_source_repo
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.unit.adoption.quality.native import conftest as native_fixture


def _supply_attempt(tmp_path: Path) -> tuple[Path, Gate]:
    root = committed_source_repo(
        tmp_path,
        {
            "pyproject.toml": '[project]\nname = "observer-sample"\nversion = "0.1.0"\n',
            ".config/ruff.toml": '[lint]\nselect = ["F"]\n',
            "src/app.py": "value = 1\n",
        },
    )
    command = (
        sys.executable,
        "-B",
        "-c",
        (
            "import json,os,sys; from pathlib import Path; "
            "Path(sys.argv[2]).write_text(json.dumps({"
            "'requirement':os.getenv('ETHOS_NATIVE_OBSERVER_REQUIREMENT'),"
            "'runtime_digest':os.getenv('ETHOS_NATIVE_OBSERVER_RUNTIME_DIGEST')}))"
        ),
        "--report",
        "{native_output}/nox.json",
    )
    gate = Gate.model_validate(
        {
            "id": "observer-supply",
            "kind": "test",
            "command": command,
            "verification_providers": ("ethos.adapters.gates.python_quality:static_report",),
            "native_outputs": (
                {"path": "nox.json", "format": "nox-json", "sessions": ("static",)},
                {"path": "ruff.sarif", "format": "sarif", "sessions": ("static",)},
                {
                    "path": "runtime.json",
                    "format": "python-runtime-json",
                    "sessions": ("static",),
                    "python": f"{sys.version_info.major}.{sys.version_info.minor}",
                    "configuration": ".config/ruff.toml",
                    "dependency_groups": (),
                },
            ),
        }
    )
    return root, gate


def test_native_attempt_supplies_and_retains_the_selected_wheel(tmp_path: Path) -> None:
    """The attempt exports exact selected supply even when its parent is source-loaded."""
    root, gate = _supply_attempt(tmp_path)
    install_fixture_hook_runtime(root)
    common = Path(git_common_dir(root))
    selected = current_runtime(common)
    wheel = common / "ethos/packages" / selected.wheel_sha256 / "ethos-fixture.whl"
    requirement = f"ethos @ {wheel.as_uri()}#sha256={selected.wheel_sha256}"
    completed, evidence = native_attempt(root, gate, gate.command, timeout=15)
    assert completed.returncode == 0, completed.stderr
    supplied = json.loads(evidence.outputs[0][1])
    assert supplied == {"requirement": requirement, "runtime_digest": selected.digest}
    execution = retained_execution(
        NativeExecution(
            gate_execution_identity(gate),
            tuple(completed.args),
            root.resolve(),
            completed.returncode,
            completed.stdout,
            completed.stderr,
            executable=gate.command[0],
            evidence=evidence,
        )
    )
    assert execution.evidence is not None
    with ZipFile(execution.evidence.artifact) as archive:
        custody = json.loads(archive.read("execution.json"))
    assert custody["observer"] == {
        "requirement": requirement,
        "runtime_digest": selected.digest,
        "wheel_sha256": selected.wheel_sha256,
    }
    assert not Path(custody["output_root"]).exists()


@pytest.mark.parametrize("boundary", ["selection", "missing-wheel", "changed-wheel"])
def test_native_attempt_refuses_unsupplied_or_changed_selected_bytes(
    tmp_path: Path, boundary: str
) -> None:
    """An ambient source import cannot replace missing or altered selected supply."""
    root, gate = _supply_attempt(tmp_path)
    reason = "hook_runtime_current_missing"
    if boundary != "selection":
        install_fixture_hook_runtime(root)
        common = Path(git_common_dir(root))
        selected = current_runtime(common)
        wheel = common / "ethos/packages" / selected.wheel_sha256 / "ethos-fixture.whl"
        if boundary == "missing-wheel":
            wheel.unlink()
        else:
            wheel.write_bytes(b"changed selected wheel\n")
            assert hashlib.sha256(wheel.read_bytes()).hexdigest() != selected.wheel_sha256
        reason = "hook_runtime_wheel_provenance_missing"
    completed, evidence = native_attempt(root, gate, gate.command, timeout=15)
    assert completed.returncode == 1
    assert evidence.gaps == (reason,)
    assert evidence.outputs == ()


def test_non_python_native_attempt_does_not_require_observer_supply(tmp_path: Path) -> None:
    """A real Node command without Python observers has no runtime-wheel prerequisite."""
    node = shutil.which("node")
    assert node is not None
    root = committed_source_repo(
        tmp_path,
        {"src/app.mjs": "export const answer = 42;\n", "package.json": '{"name":"sample"}\n'},
    )
    command = (
        node,
        "-e",
        (
            "console.log(JSON.stringify({"
            "requirement:process.env.ETHOS_NATIVE_OBSERVER_REQUIREMENT ?? null,"
            "runtime_digest:process.env.ETHOS_NATIVE_OBSERVER_RUNTIME_DIGEST ?? null}))"
        ),
        "--",
        "--report",
        "{native_output}/nox.json",
    )
    gate = Gate.model_validate({"id": "non-python", "kind": "test", "command": command})
    completed, evidence = native_attempt(root, gate, command, timeout=15)
    assert completed.returncode == 0, completed.stderr
    assert evidence.gaps == ()
    assert json.loads(completed.stdout) == {"requirement": None, "runtime_digest": None}
    assert evidence.observer is None


def test_child_ruff_owns_its_actual_interpreter_and_one_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Custody runs in the child operation, not around a parent's Nox Session.run."""
    wheel = tmp_path / "ethos-fixture.whl"
    wheel.write_bytes(b"source unit observer fixture\n")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    observer = ObserverIdentity(f"ethos @ {wheel.as_uri()}#sha256={digest}", "a" * 64, digest)
    monkeypatch.setattr(
        custody,
        "runtime_identity",
        lambda: {
            "executable": sys.executable,
            "version": list(sys.version_info[:3]),
            "prefix": sys.prefix,
            "observer": observer.to_payload(),
        },
    )
    configuration = tmp_path / "ruff.toml"
    configuration.write_text('[lint]\nselect = ["F"]\n')
    source = tmp_path / "sample.py"
    source.write_text("value = 1\n")
    binary = Path(sys.executable).with_name("ruff.exe" if sys.platform == "win32" else "ruff")
    command = (
        str(binary),
        "check",
        "--config",
        str(configuration),
        "--verbose",
        "--no-cache",
        "--output-format",
        "json",
        str(source),
    )
    runtime = tmp_path / "runtime.json"
    assert (
        custody.run_ruff(
            command, runtime_output=runtime, identity="static", configuration=configuration
        )
        == 0
    )
    observed = json.loads(runtime.read_bytes())
    assert observed["executable"] == sys.executable
    assert observed["prefix"] == sys.prefix
    assert observed["observer"] == observer.to_payload()
    assert observed["ruff"]["executable"] == str(binary)
    assert observed["ruff"]["argv"] == list(command)
    assert observed["ruff"]["launches"] == 1
    assert observed["ruff"]["completed"] is True
    assert json.loads(observed["ruff"]["stdout"]) == []
    assert "Using user-specified configuration file at:" in observed["ruff"]["stderr"]


@pytest.mark.parametrize(
    "boundary",
    [
        "valid",
        "url-hash",
        "missing",
        "missing-hash",
        "editable",
        "wrong-wheel",
        "wrong-hash",
        "conflicting-hash",
    ],
)
def test_loaded_observer_requires_exact_supplied_pep610_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    """Source-only metadata injection exercises validation, not installed behavior."""
    wheel = tmp_path / "ethos-fixture.whl"
    wheel.write_bytes(b"source unit observer fixture\n")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    requirement = f"ethos @ {wheel.as_uri()}#sha256={digest}"
    monkeypatch.setenv("ETHOS_NATIVE_OBSERVER_REQUIREMENT", requirement)
    monkeypatch.setenv("ETHOS_NATIVE_OBSERVER_RUNTIME_DIGEST", "a" * 64)
    record = {"url": wheel.as_uri(), "archive_info": {"hashes": {"sha256": digest}}}
    if boundary == "url-hash":
        record = {"url": f"{wheel.as_uri()}#sha256={digest}", "archive_info": {}}
    elif boundary == "missing":
        monkeypatch.delenv("ETHOS_NATIVE_OBSERVER_REQUIREMENT")
    elif boundary == "missing-hash":
        record["archive_info"] = {}
    elif boundary == "editable":
        record["dir_info"] = {"editable": True}
    elif boundary == "wrong-wheel":
        record["url"] = (tmp_path / "other.whl").as_uri()
    elif boundary == "wrong-hash":
        record["archive_info"] = {"hashes": {"sha256": "b" * 64}}
    elif boundary == "conflicting-hash":
        record["url"] = f"{wheel.as_uri()}#sha256={digest}"
        record["archive_info"] = {"hashes": {"sha256": "b" * 64}}
    metadata = SimpleNamespace(
        read_text=lambda _name: json.dumps(record),
        locate_file=lambda _name: Path(native_observer.__file__).parents[2],
    )
    monkeypatch.setattr(native_observer, "distribution", lambda _name: metadata)
    if boundary in {"valid", "url-hash"}:
        identity = native_observer.observer_identity()
        assert identity.to_payload() == {
            "requirement": requirement,
            "runtime_digest": "a" * 64,
            "wheel_sha256": digest,
        }
    else:
        with pytest.raises(ValueError, match="python_native_observer"):
            native_observer.observer_identity()


@pytest.mark.parametrize("executable", [None, r"C:\Program Files\Ruff\ruff.exe"])
@pytest.mark.parametrize("matching", [True, False])
def test_child_ruff_windows_audit_requires_exact_native_command_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, executable: str | None, *, matching: bool
) -> None:
    """Windows pre-spawn strings bind only through stdlib's original-argv encoding."""
    configuration = tmp_path / "ruff.toml"
    configuration.write_text('[lint]\nselect = ["F"]\n')
    command = (
        r"C:\Program Files\Ruff\ruff.exe",
        "check",
        "--config",
        str(configuration),
        'source with "quotes".py',
        "tests\\",
    )
    monkeypatch.setattr(
        custody,
        "runtime_identity",
        lambda: {"executable": sys.executable, "prefix": sys.prefix},
    )

    def run_native(arguments, **_options):
        assert arguments == command
        native = subprocess.list2cmdline(arguments if matching else (*arguments, "other.py"))
        sys.audit("subprocess.Popen", executable, native, str(tmp_path), {})
        return subprocess.CompletedProcess(arguments, 0)

    monkeypatch.setattr(custody.subprocess, "run", run_native)
    output = tmp_path / "runtime.json"
    assert (
        custody.run_ruff(
            command, runtime_output=output, identity="static-windows", configuration=configuration
        )
        == 0
    )
    observed = json.loads(output.read_bytes())["ruff"]
    assert observed["launches"] == int(matching)
    assert observed["executable"] == (command[0] if matching else "")
    if matching:
        assert observed["argv"] == list(command)
        assert observed["cwd"] == str(tmp_path)


def test_native_fixture_reclaims_scratch_when_setup_copy_fails(tmp_path, monkeypatch) -> None:
    """The fixture owns setup scratch before its first fallible preparation."""
    wheel = tmp_path / "selected.whl"
    wheel.write_bytes(b"test supply")
    scratch = tmp_path / "owned-supply"
    scratch.mkdir()
    monkeypatch.setenv("ETHOS_TEST_OBSERVER_WHEEL", str(wheel))
    monkeypatch.setattr(native_fixture, "wheel_build_identity", lambda _: None)

    def failed_copy(*_args) -> None:
        message = "fixture_copy_failed"
        raise OSError(message)

    monkeypatch.setattr(native_fixture.shutil, "copyfile", failed_copy)
    factory = SimpleNamespace(mktemp=lambda _name: scratch)
    fixture = inspect.unwrap(native_fixture.native_nox_supply)(factory)
    with pytest.raises(OSError, match="fixture_copy_failed"):
        next(fixture)
    assert not scratch.exists()
