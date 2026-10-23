"""Keep runtime fixtures source-bound without copying the dependency tree."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tomllib
from pathlib import Path
from unittest.mock import Mock

import pytest

import tests.support.governed_repository as fixtures
import tests.support.runtime_scenarios as runtime_scenarios
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import prepared_work_lane
from tests.support.proof import seed_executed_proof


def test_generic_work_lane_fixture_uses_a_minimal_valid_hook_runtime(tmp_path, monkeypatch):
    """Generic state setup does not rerun the unrelated public start workflow."""
    monkeypatch.setattr(
        fixtures, "run_ethos", lambda *_a, **_kw: pytest.fail("redundant lane start")
    )
    fixture = prepared_work_lane(tmp_path)
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
    starts = Mock(wraps=subprocess.Popen)
    monkeypatch.setattr(subprocess, "Popen", starts)
    assert hook_runtime_binding(fixture.worktree)["required_gaps"] == []
    assert all("/ethos/runtime/" not in str(call.args[0][0]) for call in starts.call_args_list)
    assert len(files) <= 6
    assert payload_bytes < 1_000_000
    config = (common / "config").read_bytes()
    work_config = Path(fixtures.git(fixture.worktree, "rev-parse", "--git-path", "config.worktree"))
    assert not work_config.exists()
    seed_executed_proof(fixture.worktree, fixtures.git(fixture.worktree, "rev-parse", "HEAD"))
    assert (common / "config").read_bytes() == config
    assert not work_config.exists()
    sibling = prepared_work_lane(tmp_path / "sibling", holder_ref="agent:test:case:sibling")
    assert git_common_dir(sibling.worktree) != git_common_dir(fixture.worktree)
    (fixture.worktree / "README.md").write_text("unique source work\n")
    assert (sibling.worktree / "README.md").read_text() == "# sample\n"
    assert (
        leases_by_branch(sibling.worktree)["work/feature"]["holder_ref"]
        == "agent:test:case:sibling"
    )


def test_documentation_fixture_gate_observes_committed_requirements(tmp_path: Path) -> None:
    """The neutral fixture gate must be runnable and reject an absent requirement."""
    repo = fixtures.init_git_repo(tmp_path / "repo")
    fixtures.adopt_and_commit(repo, docs_only=True)
    gate = tomllib.loads((repo / "system/gates.toml").read_text())["gates"][0]
    command = gate["command"]
    present = subprocess.run(command, cwd=repo, check=False, capture_output=True)
    assert present.returncode == 0, present.stderr

    spec = repo / "openspec/specs/contracts/spec.md"
    spec.write_text("## Requirements\n\nNo accepted requirement remains.\n")
    fixtures.commit_fixture(repo, "remove fixture requirement")
    missing = subprocess.run(command, cwd=repo, check=False, capture_output=True)
    assert missing.returncode == 1, missing.stderr


def test_fixture_commit_normalizes_selected_carriers_without_changing_other_bytes(
    tmp_path: Path,
) -> None:
    """Formatting is opt-in; malformed unselected fixture source remains exact."""
    repo = fixtures.init_git_repo(tmp_path / "repo")
    package = repo / "package.json"
    malformed = repo / "broken.js"
    original = b'{"type":"module"}\n'
    broken = b"export function broken( {\n"
    package.write_bytes(original)
    malformed.write_bytes(broken)
    fixtures.commit_fixture(repo, "retain deliberate fixture inputs")
    assert package.read_bytes() == original
    assert malformed.read_bytes() == broken

    head = fixtures.git(repo, "rev-parse", "HEAD")
    with pytest.raises(subprocess.CalledProcessError):
        fixtures.commit_fixture(
            repo, "refuse malformed selection", format_paths=("package.json", "broken.js")
        )
    assert package.read_bytes() == original
    assert malformed.read_bytes() == broken
    assert fixtures.git(repo, "rev-parse", "HEAD") == head
    assert not fixtures.git(repo, "status", "--porcelain=v1")

    fixtures.commit_fixture(repo, "normalize selected carrier", format_paths=("package.json",))

    assert package.read_bytes() == b'{\n  "type": "module"\n}\n'
    assert malformed.read_bytes() == broken
    assert fixtures.git(repo, "show", "HEAD:broken.js") == broken.decode().strip()
    assert not fixtures.git(repo, "status", "--porcelain=v1")


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


@pytest.mark.parametrize("gate_prefix", [True, False])
def test_isolated_fixture_python_reads_the_test_gate_bytecode_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, gate_prefix: bool
) -> None:
    """Fixture hooks run isolated, so the gate's shared bytecode reaches them through the image."""
    prefix = str(tmp_path / "python-bytecode") if gate_prefix else None
    monkeypatch.setattr(sys, "pycache_prefix", prefix)
    image = tmp_path / "image"
    runtime_scenarios.create_fixture_python(image)

    completed = subprocess.run(
        (
            str(runtime_scenarios.runtime_executable(image, "python")),
            "-B",
            "-I",
            "-c",
            "import sys; print(sys.pycache_prefix)",
        ),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )

    assert (completed.stdout.strip(), completed.stderr) == (str(prefix), "")
