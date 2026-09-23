"""Native test-gate scheduling, coverage evidence and resource ownership."""

from __future__ import annotations

import tomllib
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast

import pytest

import tools.ci.python_test_gate as python_test_gate
from ethos.adapters.process import run_command
from ethos.contracts.gates import GateRegistryDeclaration
from tests.support.runtime_scenarios import empty_node_package_supply
from tests.support.subprocesses import kill_after_marker

if TYPE_CHECKING:
    from pathlib import Path

    import nox

import os
import subprocess


@pytest.mark.parametrize("failure", ["none", "cached", "crash", "assertion"])
def test_parallel_python_test_gate_bounds_failed_attempt_without_replay(
    tmp_path: Path, monkeypatch, failure: str
) -> None:
    """The native owner stops failed work, preserves success coverage and reclaims scratch."""
    config = tomllib.loads(python_test_gate.PYTEST_CONFIG.read_text())
    assert "timeout_method" not in config["pytest"]
    gate = _test_gate(tmp_path, workers=2)
    failed = failure not in {"none", "cached"}
    cache = tmp_path / "cache"
    if failure == "cached":
        (cache / "v/cache").mkdir(parents=True)
        (cache / "v/cache/lastfailed").write_text('{"test_queue.py::test_worker_loss[79]": true}')
    (tmp_path / "conftest.py").write_text(
        "from pathlib import Path\ndef pytest_testnodedown(node, error):\n"
        "    if error: Path(__file__).with_name('failed').touch()\n"
        "def pytest_runtest_logreport(report):\n"
        "    if report.failed: Path(__file__).with_name('failed').touch()\n"
    )
    test = tmp_path / "test_queue.py"
    test.write_text(
        f"""import os, time
from pathlib import Path
import pytest

@pytest.mark.parametrize("index", range(80))
def test_worker_loss(index):
    with (Path(__file__).parent / f"case-{{index}}").open("a") as stream:
        stream.write("after\\n" if Path(__file__).with_name("failed").exists() else "before\\n")
    if index == 0 and {failure!r} == 'crash':
        os._exit(86)
    assert index != 0 or {failure!r} != 'assertion'
    time.sleep(0.05)
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(python_test_gate, "ROOT", tmp_path)
    monkeypatch.setattr(python_test_gate, "_head", lambda: gate.s.head)
    monkeypatch.setattr(python_test_gate, "TARGETS", (str(test),))
    observed = []

    def execute(*command: str, env, **_kwargs) -> None:
        result = run_command(
            tmp_path,
            (*command, "--no-cov", "-o", f"cache_dir={cache}"),
            timeout=30,
            env={key: value for key, value in env.items() if value is not None},
            remove_env=tuple(key for key, value in env.items() if value is None),
            remove_env_prefixes=("COVERAGE",),
        )
        observed.append(result)
        result.check_returncode()

    try:
        gate.run_tests(cast("nox.Session", SimpleNamespace(run=execute)))
    except subprocess.CalledProcessError:
        assert failed
    (result,) = observed
    assert (result.returncode != 0) is failed, result.stdout + result.stderr
    observations = [path.read_text().strip() for path in tmp_path.glob("case-*")]
    assert set(observations) <= {"before", "after"}
    assert (tmp_path / "case-0").read_text() == "before\n"
    assert observations.count("after") <= 3 if failed else len(observations) == 80, observations
    assert gate.head_file.exists() is not failed
    assert not gate.s.basetemp.exists()
    if failure == "cached":
        assert (tmp_path / "case-79").stat().st_mtime_ns < (tmp_path / "case-40").stat().st_mtime_ns
    if failure == "crash":
        for fragment in ("worker 'gw", "crashed while running", "::test_worker_loss[0]"):
            assert fragment in result.stdout + result.stderr


@pytest.mark.parametrize("full", [False, True])
def test_coverage_gate_is_in_the_resolved_proof_closure(*, full: bool) -> None:
    declaration = GateRegistryDeclaration.model_validate(
        tomllib.loads((python_test_gate.ROOT / "system/gates.toml").read_text(encoding="utf-8"))
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
        run_command(
            tmp_path,
            (
                str(python_test_gate.PYTHON),
                "-m",
                "coverage",
                action,
                f"--rcfile={python_test_gate.COVERAGE_CONFIG}",
                f"--data-file={gate.data}",
                *args,
            ),
            env=environment,
            inherit_environment=False,
            check=True,
            timeout=10,
        )
    gate.head_file.write_text(gate.s.head + "\n", encoding="utf-8")
    before = gate.data.read_bytes()
    monkeypatch.setattr(python_test_gate, "_head", lambda: gate.s.head)
    observed = []

    def execute(*command: str, **_kwargs: object) -> None:
        observed.append(
            run_command(
                tmp_path,
                command,
                env=environment,
                inherit_environment=False,
                timeout=10,
            )
        )

    gate.enforce_floor(cast("nox.Session", SimpleNamespace(run=execute)))

    assert len(observed) == 1
    assert observed[0].returncode == exit_code, observed[0].stdout + observed[0].stderr
    assert "TOTAL" in observed[0].stdout
    assert f"{covered}.00%" in observed[0].stdout
    assert gate.data.read_bytes() == before


def _test_gate(tmp_path: Path, *, workers: int | None = None):
    return python_test_gate.PythonTestGate(
        python_test_gate.Settings(
            head="a" * 40,
            evidence=tmp_path / "evidence",
            basetemp=tmp_path / "pytest",
            basetemp_owned=True,
            workers=workers,
            shards=None,
            durations=0,
            timeout=None,
            lock_wait=0,
            uv_cache=None,
            node_package_supply=tmp_path / "node_modules",
        )
    )


@pytest.mark.parametrize("mode", [0o755, 0o555, 0o000, 0o100])
def test_python_cleanup_changes_only_required_directory_permissions(
    tmp_path, monkeypatch, mode
) -> None:
    """Deletion must not rewrite writable directories or POSIX file metadata."""
    target = tmp_path / "evidence"
    runtime = target / "repo/.git/ethos/runtime/digest"
    runtime.mkdir(parents=True)
    payload = runtime / "manifest.json"
    payload.write_text("{}\n", encoding="utf-8")
    payload.chmod(0o444)
    runtime.chmod(mode)
    chmod, changed = type(target).chmod, []

    def observe(path, mode, **kwargs):
        if path == runtime:
            assert kwargs.get("follow_symlinks", True) is (
                os.chmod not in os.supports_follow_symlinks
            )
        changed.append(path)
        return chmod(path, mode, **kwargs)

    monkeypatch.setattr(type(target), "chmod", observe)
    python_test_gate.remove_generated_path(target)

    assert not target.exists()
    if os.name == "posix":
        assert changed == ([] if mode == 0o755 else [runtime])
    python_test_gate.remove_generated_path(target)


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
    with pytest.raises(pytest.fail.Exception, match="missing or stale"):
        gate.enforce_floor(cast("nox.Session", SimpleNamespace(error=pytest.fail)))


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
import sys
from pathlib import Path
from types import SimpleNamespace
from tests.support.subprocesses import pause_after_effect
from tools.ci.python_test_gate import PythonTestGate, Settings
root = Path(sys.argv[1])
gate = PythonTestGate(Settings(
    head='a' * 40, evidence=root / 'evidence', basetemp=root / 'pytest',
    basetemp_owned=True, workers=1, shards=1, durations=0, timeout=None,
    lock_wait=0, uv_cache=None, node_package_supply=root / 'node_modules',
))
session = SimpleNamespace(run=lambda *args, **kwargs: 'executing')
pause_after_effect(session, 'run', root / 'ready')
gate.run_tests(session)
"""
    assert kill_after_marker(tmp_path, script, (str(tmp_path),), ready, timeout=15) == "executing"

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
