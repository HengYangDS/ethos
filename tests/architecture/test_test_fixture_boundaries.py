"""Keep runtime fixtures source-bound without copying the dependency tree."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.hook.observation as observation
import tests.support.runtime_scenarios as runtime_scenarios
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import start_adopted_work_lane


def test_generic_work_lane_fixture_uses_a_minimal_valid_hook_runtime(tmp_path: Path) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    common = Path(git_common_dir(fixture.repository))
    selected = current_runtime(common)
    files = tuple(path for path in selected.root.rglob("*") if path.is_file())
    source_python = Path(sys.executable).resolve()
    assert selected.python != source_python
    assert selected.python.read_bytes() == source_python.read_bytes()
    assert not selected.python.samefile(source_python)
    source_digest = hashlib.sha256(source_python.read_bytes()).digest()
    assert [
        path for path in files if hashlib.sha256(path.read_bytes()).digest() == source_digest
    ] == [selected.python]
    payload_bytes = sum(path.stat().st_size for path in files if path != selected.python)

    assert leases_by_branch(fixture.worktree)["work/feature"]["lease_state"] == "valid"
    assert hook_runtime_binding(fixture.worktree)["required_gaps"] == []
    assert len(files) <= 6
    assert payload_bytes < 1_000_000


def test_runtime_mutation_fixture_observes_native_prerequisites_before_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Selector-only validation must not expose an unexecuted fixture runtime."""
    execute = subprocess.run
    observed: list[tuple[str, ...]] = []

    def observe(command, *args, **kwargs):
        result = execute(command, *args, **kwargs)
        if not isinstance(command, str):
            values = tuple(map(str, command))
            if values and "/ethos/runtime/" in values[0].replace("\\", "/"):
                assert result.returncode == 0, result.stderr
                observed.append(values)
        return result

    monkeypatch.setattr(subprocess, "run", observe)
    _repo, runtime = runtime_scenarios.materialize_runtime_case(tmp_path, monkeypatch)
    python = runtime_scenarios.runtime_executable(runtime, "python")

    assert any(command[:4] == (str(python), "-B", "-I", "-c") for command in observed)
    assert (str(python), "-B", "-I", "-m", "ethos.cli", "--version") in observed
    assert python.stat().st_nlink == 1
    assert not python.samefile(sys.executable)


def test_runtime_fixture_rejects_failed_module_before_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real failed module startup must not become a supposedly ready fixture."""
    create = runtime_scenarios.create_fixture_python

    def broken_module(target: Path) -> None:
        create(target)
        site = next(target.rglob("ethos-fixture.pth")).parent
        (site / "ethos.py").write_text('raise RuntimeError("fixture module broken")\n')

    monkeypatch.setattr(runtime_scenarios, "create_fixture_python", broken_module)

    with pytest.raises(ValueError, match="fixture_runtime_module_smoke_failed:"):
        runtime_scenarios.materialize_runtime_case(tmp_path, monkeypatch)

    runtime_root = tmp_path / "repo/.git/ethos/runtime"
    assert not any(path.is_dir() for path in runtime_root.iterdir())


def test_matching_selected_hook_contract_does_not_start_a_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same immutable declaration inputs must not pay an unrelated startup boundary."""
    fixture = start_adopted_work_lane(tmp_path)
    execute = subprocess.run
    calls = []

    def observed(*args, **kwargs):
        if args and "/ethos/runtime/" in str(args[0][0]):
            calls.append(args)
        return execute(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", observed)
    binding = observation.hook_runtime_binding(fixture.worktree)
    assert binding["required_gaps"] == []
    assert calls == []
