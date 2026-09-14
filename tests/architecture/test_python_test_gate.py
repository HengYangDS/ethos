from __future__ import annotations

import time
import tomllib
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast

import pytest

import tools.ci.python_test_gate as python_test_gate
from ethos.contracts.gates import GateRegistryDeclaration
from tests.support.runtime_scenarios import empty_node_package_supply

if TYPE_CHECKING:
    import nox

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTEST_CONFIG = ROOT / ".config/checks/pytest/pytest.ini"


def test_parallel_python_test_gate_does_not_replay_a_crashed_worker(tmp_path: Path) -> None:
    marker = tmp_path / "executions.txt"
    test = tmp_path / "test_worker_loss.py"
    test.write_text(
        """import os
from pathlib import Path


def test_worker_loss() -> None:
    marker = Path(os.environ["ETHOS_WORKER_LOSS_MARKER"])
    with marker.open("ab", buffering=0) as stream:
        stream.write(b"executed\\n")
    os._exit(86)
""",
        encoding="utf-8",
    )
    command = [sys.executable, "-m", "pytest", "-c", str(PYTEST_CONFIG)]
    command += ["-n", "2", str(test)]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=os.environ | {"ETHOS_WORKER_LOSS_MARKER": str(marker)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert marker.read_text(encoding="utf-8") == "executed\n"
    output = result.stdout + result.stderr
    for fragment in ("worker 'gw", "crashed while running", "::test_worker_loss"):
        assert fragment in output


@pytest.mark.parametrize("full", [False, True])
def test_coverage_gate_is_in_the_resolved_proof_closure(*, full: bool) -> None:
    declaration = GateRegistryDeclaration.model_validate(
        tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    )
    selected = declaration.proof_gates(full=full, python_executable=str(python_test_gate.PYTHON))
    identifiers = [gate.id for gate in selected]
    assert identifiers.count("coverage-floor") == 1
    assert identifiers.index("unit-architecture") < identifiers.index("coverage-floor")
    gate = selected[identifiers.index("coverage-floor")]
    assert gate.command == (str(python_test_gate.PYTHON), "-m", "nox", "-s", "coverage_floor")


@pytest.mark.parametrize(("covered", "exit_code"), [(94, 2), (95, 0)])
def test_coverage_floor_rejects_below_required_measurement(
    tmp_path, monkeypatch, covered, exit_code
):
    subject = tmp_path / "subject.py"
    subject.write_text(
        "def uncalled():\n" + "    value = 0\n" * (100 - covered) + "value = 1\n" * (covered - 1),
        encoding="utf-8",
    )
    gate = _test_gate(tmp_path)
    gate.coverage.mkdir(parents=True)
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("COVERAGE")
    }
    for action, args in (("run", (f"--source={tmp_path}", str(subject))), ("combine", ())):
        subprocess.run(
            [
                str(python_test_gate.PYTHON),
                "-m",
                "coverage",
                action,
                f"--rcfile={python_test_gate.COVERAGE_CONFIG}",
                f"--data-file={gate.data}",
                *args,
            ],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
    gate.head_file.write_text(gate.s.head + "\n", encoding="utf-8")
    before = gate.data.read_bytes()
    monkeypatch.setattr(python_test_gate, "_head", lambda: gate.s.head)
    observed = []

    class Session:
        @staticmethod
        def run(*command: str, **_kwargs: object) -> None:
            observed.append(
                subprocess.run(
                    command,
                    cwd=tmp_path,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            )

    gate.enforce_floor(cast("nox.Session", Session()))

    assert len(observed) == 1
    assert observed[0].returncode == exit_code, observed[0].stdout + observed[0].stderr
    assert "TOTAL" in observed[0].stdout
    assert f"{covered}.00%" in observed[0].stdout
    assert gate.data.read_bytes() == before


def _test_gate(tmp_path: Path):
    return python_test_gate.PythonTestGate(
        python_test_gate.Settings(
            head="a" * 40,
            evidence=tmp_path / "evidence",
            basetemp=tmp_path / "pytest",
            basetemp_owned=True,
            workers=None,
            shards=None,
            durations=0,
            timeout=None,
            lock_wait=0,
            uv_cache=None,
            node_package_supply=tmp_path / "node_modules",
        )
    )


def test_python_cleanup_propagates_removal_failure(tmp_path, monkeypatch) -> None:
    target = tmp_path / "evidence"
    target.mkdir()

    def denied(_path: Path) -> None:
        message = "cleanup denied"
        raise OSError(message)

    monkeypatch.setattr(python_test_gate.shutil, "rmtree", denied)
    with pytest.raises(OSError, match="cleanup denied"):
        python_test_gate.remove_generated_path(target)


def test_python_cleanup_removes_owned_readonly_runtime_tree(tmp_path) -> None:
    target = tmp_path / "evidence"
    runtime = target / "repo/.git/ethos/runtime/digest"
    runtime.mkdir(parents=True)
    payload = runtime / "manifest.json"
    payload.write_text("{}\n", encoding="utf-8")
    payload.chmod(0o444)
    runtime.chmod(0o555)

    python_test_gate.remove_generated_path(target)

    assert not target.exists()


@pytest.mark.parametrize("relation", ["root-link", "nested-link", "hardlink"])
def test_python_cleanup_preserves_external_content_and_permissions(tmp_path, relation) -> None:
    """Owned cleanup unlinks references without changing an external inode."""
    outside = tmp_path / "outside"
    outside.mkdir()
    payload = outside / "payload"
    payload.write_bytes(b"external content")
    target = tmp_path / "owned"
    if relation == "root-link":
        target.symlink_to(outside, target_is_directory=True)
    else:
        target.mkdir()
        if relation == "nested-link":
            (target / "link").symlink_to(outside, target_is_directory=True)
        else:
            os.link(payload, target / "link")
    payload.chmod(0o444)
    before = payload.stat()

    python_test_gate.remove_generated_path(target)

    assert not target.exists()
    assert not target.is_symlink()
    after = payload.stat()
    assert payload.read_bytes() == b"external content"
    assert (after.st_ino, after.st_mode, after.st_mtime_ns) == (
        before.st_ino,
        before.st_mode,
        before.st_mtime_ns,
    )


@pytest.mark.parametrize("failure", ["prepare", "test", "cleanup", "freshness"])
def test_python_attempt_revokes_previous_success_before_any_work(
    tmp_path, monkeypatch, failure
) -> None:
    """A same-HEAD failure cannot retain a previous attempt's success marker."""
    gate = _test_gate(tmp_path)
    monkeypatch.setattr(python_test_gate, "ROOT", tmp_path)
    monkeypatch.setattr(
        python_test_gate, "_head", lambda: "b" * 40 if failure == "freshness" else gate.s.head
    )
    gate.coverage.mkdir(parents=True)
    gate.head_file.write_text(gate.s.head + "\n")
    gate.data.write_bytes(b"old evidence")
    remove = python_test_gate.remove_generated_path

    def execute(*_args, **_kwargs) -> None:
        assert not gate.head_file.exists()
        if failure == "test":
            raise KeyboardInterrupt

    calls = 0

    def clean(path: Path) -> None:
        nonlocal calls
        if path == tmp_path / ".coverage":
            assert not gate.head_file.exists()
            calls += 1
            if (failure == "prepare" and calls == 1) or (failure == "cleanup" and calls == 2):
                message = f"{failure} failed"
                raise RuntimeError(message)
        remove(path)

    monkeypatch.setattr(python_test_gate, "remove_generated_path", clean)
    with pytest.raises(KeyboardInterrupt if failure == "test" else RuntimeError):
        gate.run_tests(cast("nox.Session", SimpleNamespace(run=execute)))

    assert not gate.head_file.exists()
    session = SimpleNamespace(error=pytest.fail)
    with pytest.raises(pytest.fail.Exception, match="missing or stale"):
        gate.enforce_floor(cast("nox.Session", session))


def test_python_single_attempt_discards_partial_and_sharded_outputs(tmp_path, monkeypatch) -> None:
    """An interrupted attempt's data cannot silently join a new test population."""
    gate = _test_gate(tmp_path)
    monkeypatch.setattr(python_test_gate, "ROOT", tmp_path)
    monkeypatch.setattr(python_test_gate, "_head", lambda: gate.s.head)
    gate.coverage.mkdir(parents=True)
    (gate.pytest / "shards").mkdir(parents=True)
    for name in (".coverage", ".coverage.worker", ".coverage.shard-1", "coverage.xml"):
        (gate.coverage / name).write_bytes(b"stale")
    for name in ("junit.xml", "junit-shard-1.xml", "nodeids.txt", "shards/shard-1.passed"):
        (gate.pytest / name).write_bytes(b"stale")

    def run(*_args, **_kwargs) -> None:
        assert not list(gate.coverage.glob(".coverage*"))
        assert not (gate.coverage / "coverage.xml").exists()
        assert not tuple(gate.pytest.iterdir())
        assert not gate.head_file.exists()

    gate.run_tests(cast("nox.Session", SimpleNamespace(run=run)))

    assert gate.head_file.read_text() == gate.s.head + "\n"
    assert not gate.s.basetemp.exists()


def test_killed_python_attempt_cannot_reuse_previous_completion(tmp_path, monkeypatch) -> None:
    """An actual process kill cannot revive a prior same-source success marker."""
    gate = _test_gate(tmp_path)
    gate.coverage.mkdir(parents=True)
    gate.data.write_bytes(b"old coverage")
    gate.head_file.write_text(gate.s.head + "\n")
    ready = tmp_path / "ready"
    script = """
import sys, time
from pathlib import Path
from types import SimpleNamespace
from tools.ci.python_test_gate import PythonTestGate, Settings
root = Path(sys.argv[1])
gate = PythonTestGate(Settings(
    head='a' * 40, evidence=root / 'evidence', basetemp=root / 'pytest',
    basetemp_owned=True, workers=1, shards=1, durations=0, timeout=None,
    lock_wait=0, uv_cache=None, node_package_supply=root / 'node_modules',
))
def execute(*args, **kwargs):
    (root / 'ready').write_text('executing')
    time.sleep(60)
gate.run_tests(SimpleNamespace(run=execute))
"""
    environment = os.environ | {"PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "src")))}
    with subprocess.Popen(
        [str(python_test_gate.PYTHON), "-B", "-c", script, str(tmp_path)],
        cwd=tmp_path,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        try:
            deadline = time.monotonic() + 15
            while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            assert ready.exists(), "test owner did not enter native execution"
            process.kill()
            process.communicate(timeout=10)
            assert process.returncode != 0
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)

    assert not gate.head_file.exists()
    monkeypatch.setattr(python_test_gate, "_head", lambda: gate.s.head)
    with pytest.raises(pytest.fail.Exception, match="missing or stale"):
        gate.enforce_floor(cast("nox.Session", SimpleNamespace(error=pytest.fail)))


@pytest.mark.parametrize(
    ("failure", "ownership"),
    [("", "owned"), ("pytest", "owned"), ("prepare", "owned"), ("", "external")],
)
def test_python_basetemp_ownership(tmp_path, monkeypatch, failure, ownership) -> None:
    root, external = tmp_path / "repo", tmp_path / "external"
    empty_node_package_supply(root)
    monkeypatch.setattr(python_test_gate, "ROOT", root)
    monkeypatch.setattr(python_test_gate.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(python_test_gate, "_head", lambda: "a" * 40)
    monkeypatch.delenv("ETHOS_TEST_BASETEMP", raising=False)
    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)
    if ownership == "external":
        monkeypatch.setenv("ETHOS_TEST_BASETEMP", str(external))
    gate = python_test_gate.PythonTestGate.from_environment(
        node_package_supply=root / "node_modules"
    )
    cache = root / "src/ethos/__pycache__"
    cache.mkdir(parents=True)
    monkeypatch.setattr(gate, "_stable_head", lambda: None)

    def fail(*_args: object) -> None:
        gate.s.basetemp.mkdir(parents=True, exist_ok=True)
        message = f"{failure} failed"
        raise RuntimeError(message)

    monkeypatch.setattr(
        gate,
        "_prepare" if failure == "prepare" else "_single",
        fail if failure else lambda *_: None,
    )
    if failure:
        with pytest.raises(RuntimeError, match=failure):
            gate.run_tests(cast("nox.Session", object()))
    else:
        gate.run_tests(cast("nox.Session", object()))

    assert (gate.s.basetemp.exists(), cache.is_dir()) == (ownership == "external", True)
