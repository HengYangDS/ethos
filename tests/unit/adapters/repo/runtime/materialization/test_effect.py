"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
import ethos.adapters.repo.runtime.materialization.python_environment as runtime_python_environment
import tests.support.runtime_scenarios as runtime_scenarios
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_environment
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.transition import PackageArtifact
from tests.support.runtime_scenarios import REPOSITORY_ROOT
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import runtime_build


def _environment(**changes: str):
    values = {
        "python_abi": "cpython-test",
        "python_version": "3.14.7",
        "python_implementation": "cpython",
        "dependency_lock_sha256": "d" * 64,
        "platform_name": "test",
        "architecture_name": "test-architecture",
    }
    return runtime_environment(**(values | changes))


def _python_facts(home: Path) -> dict[str, str]:
    environment = _environment()
    return {
        key: str(value)
        for key, value in {
            **environment._asdict(),
            "executable": (home / "bin/python").resolve(),
            "base_executable": (home / "bin/python").resolve(),
            "prefix": home,
            "base_prefix": home,
        }.items()
    }


def _write(path: Path, payload: bytes = b"payload") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _generation_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    runtime_root, source = tmp_path / "runtime", tmp_path / "source"
    work, interpreter, wheel = runtime_root / ".work", tmp_path / "python", tmp_path / "ethos.whl"
    source.mkdir()
    _write(interpreter, b"python")
    _write(wheel, b"wheel")
    artifact = PackageArtifact(wheel, "c" * 64, runtime_build("a" * 40, "b" * 40))

    def materialize_python(target: Path, *_args: object, **_kwargs: object) -> None:
        for relative, payload in (("bin/python", b"python"), ("bin/ethos", b"ethos")):
            _write(target / relative, payload)

    observed: list[Path] = []
    inventory = runtime_materialization.runtime_file_inventory
    for name, implementation in {
        "materialize_python_image": materialize_python,
        "runtime_file_inventory": lambda root: observed.append(root) or inventory(root),
        "observe_python_facts": lambda python: dict.fromkeys(
            ("prefix", "base_prefix"), python.parent.parent.resolve().as_posix()
        ),
    }.items():
        monkeypatch.setattr(runtime_materialization, name, implementation)

    command = Mock(return_value=subprocess.CompletedProcess([], 0, "0.2.0-alpha.5\n", ""))
    monkeypatch.setattr(runtime_materialization.subprocess, "run", command)
    return (runtime_root, work, source, interpreter, artifact, _environment()), observed, command


@pytest.mark.parametrize("supply", ["packaged", "split-image", "source", "selected"])
def test_runtime_materialization_binds_package_dependency_and_image_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, supply: str
) -> None:
    """Package, source, and selected-runtime supply preserve their own coordinates."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(("git", "init", "--quiet", "--initial-branch=dev"), cwd=repo, check=True)
    source_file = runtime_materialization.__file__
    package = Path(source_file).resolve().parents[6]
    project = tmp_path / "runtime-project"
    invoked = _write(tmp_path / "managed-python/bin/python", b"python")
    dependency = project / ".venv/bin/python" if supply == "source" else invoked
    image = (
        tmp_path / "native-python" if supply in {"source", "split-image"} else invoked.parent.parent
    )
    facts = _python_facts(image)
    interpreter = Path(facts["executable"])
    wheel = _write(tmp_path / "ethos.whl", b"wheel")
    requirements = _write(tmp_path / "requirements.txt", b"package==1\n")
    artifact = PackageArtifact(wheel, "c" * 64, runtime_build("a" * 40, "b" * 40))
    environment = _environment()
    observed: dict[str, object] = {}

    def record(key: str, value: object, result: object) -> object:
        observed[key] = value
        return result

    def generation(_root, _work, source, python, package_artifact, actual_environment, **kwargs):
        return record(
            "generation",
            (source, python, package_artifact, actual_environment, kwargs),
            tmp_path / "runtime-generation",
        )

    patches = {
        "resolve_runtime_project": lambda _root: project,
        "resolve_locked_environment_python": lambda _root: dependency,
        "_reusable_runtime": lambda *_args: None,
        "is_selected_runtime_source": lambda _source: supply == "selected",
        "require_python_image_source": lambda python: record("image_source", python, facts),
        "observe_runtime_environment": lambda source, python, **kwargs: record(
            "environment", (source, python, kwargs["python_facts"]), environment
        ),
        "prepare_locked_requirements": lambda source, _work, python, **kwargs: record(
            "prepared", (source, python, kwargs["require_build_tools"]), requirements
        ),
        "resolve_runtime_wheel": lambda source, _work, *, python: record(
            "wheel", (source, python), wheel
        ),
        "materialize_package_wheel": lambda *_args, **_kwargs: artifact,
        "materialize_runtime_generation": generation,
    }
    for name, value in patches.items():
        monkeypatch.setattr(runtime_materialization, name, value)

    assert runtime_materialization.__file__ == source_file
    result = runtime_materialization.materialize_runtime(
        repo,
        invoked,
        expected_build=artifact.build,
        build_source=project if supply == "source" else None,
    )

    expected = {
        "image_source": dependency,
        "environment": (project, interpreter, facts),
        "wheel": (project if supply == "source" else package, dependency),
        "generation": (
            project,
            interpreter,
            artifact,
            environment,
            {
                "dependency_python": None if supply == "selected" else dependency,
                "python_facts": facts,
                "locked_requirements": None if supply == "selected" else requirements,
            },
        ),
    }
    if supply != "selected":
        expected["prepared"] = (project, dependency, supply == "source")
    assert observed == expected
    assert result == tmp_path / "runtime-generation/python"


def test_runtime_generation_hashes_only_prepared_and_exposed_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, observed, commands = _generation_case(tmp_path, monkeypatch)
    runtime_root, environment = args[0], args[5]
    target = runtime_materialization.materialize_runtime_generation(*args, locked_requirements=None)

    commands.assert_called_once()
    command = commands.call_args.args[0]
    assert command == (
        runtime_materialization.runtime_python(command[0].parent.parent),
        "-B",
        "-I",
        "-m",
        "ethos.cli",
        "--version",
    )
    assert len(observed) == 2
    assert observed[0].name.startswith(".runtime-build-")
    assert observed[1] == target
    assert stat.S_IMODE(target.stat().st_mode) & 0o222 == 0
    assert stat.S_IMODE((target / "manifest.json").stat().st_mode) & 0o222 == 0
    assert all(
        path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o222 == 0
        for path in target.rglob("*")
    )
    assert (
        runtime_materialization.materialize_runtime_generation(*args, locked_requirements=None)
        == target
    )
    is_dir = Path.is_dir
    mode = stat.S_IMODE(runtime_root.stat().st_mode)
    runtime_root.chmod(mode | stat.S_IWUSR)
    with monkeypatch.context() as context:
        seen: set[Path] = set()
        context.setattr(
            Path,
            "is_dir",
            lambda path: is_dir(path) if path != target or path in seen else bool(seen.add(path)),
        )
        context.setattr(
            Path, "rename", lambda _path, _target: (_ for _ in ()).throw(FileExistsError)
        )
        assert (
            runtime_materialization.materialize_runtime_generation(*args, locked_requirements=None)
            == target
        )
    runtime_root.chmod(mode)
    with monkeypatch.context() as context:
        context.setattr(runtime_materialization, "runtime_file_inventory", lambda _root: {})
        with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
            runtime_materialization.require_runtime_generation(target, args[4], environment)
    with monkeypatch.context() as context:
        context.setattr(
            runtime_materialization,
            "observe_python_facts",
            lambda _python: {"prefix": "wrong", "base_prefix": "wrong"},
        )
        with pytest.raises(ValueError, match="hook_runtime_python_not_relocatable"):
            runtime_materialization.require_runtime_generation(target, args[4], environment)


@pytest.mark.parametrize("failure", [ValueError, subprocess.TimeoutExpired, KeyboardInterrupt])
def test_failed_runtime_verification_removes_only_its_new_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: type[BaseException]
) -> None:
    """Reject failed verification without retaining unverified or deleting accepted bytes."""
    execute = subprocess.run
    args, _observed, _commands = _generation_case(tmp_path, monkeypatch)
    target = runtime_materialization.materialize_runtime_generation(*args, locked_requirements=None)

    preserved = runtime_materialization.runtime_file_inventory(target)

    def failed_verification(*_args, **_kwargs):
        if failure is ValueError:
            return subprocess.CompletedProcess([], 7, "out", "failed")
        if failure is KeyboardInterrupt:
            raise KeyboardInterrupt
        return execute([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.1)

    monkeypatch.setattr(runtime_materialization.subprocess, "run", failed_verification)
    pattern = (
        r"hook_runtime_module_smoke_failed:command=.*python -B -I -m ethos\.cli "
        "--version:returncode=7:stdout=out:stderr=failed"
    )
    with pytest.raises(failure, match=pattern if failure is ValueError else None):
        runtime_materialization.materialize_runtime_generation(
            *args[:-1], _environment(architecture_name="other"), locked_requirements=None
        )
    assert {path for path in args[0].iterdir() if path.is_dir()} == {target}
    assert runtime_materialization.runtime_file_inventory(target) == preserved


def test_runtime_generation_compares_windows_prefixes_as_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, _observed, _commands = _generation_case(tmp_path, monkeypatch)
    target = runtime_materialization.materialize_runtime_generation(*args, locked_requirements=None)
    prefix = (target / "python").resolve().as_posix()
    windows_spelling = prefix.replace("/", "\\").upper()
    monkeypatch.setattr(
        runtime_python_environment,
        "os",
        SimpleNamespace(name="nt", fspath=os.fspath),
    )
    monkeypatch.setattr(
        runtime_materialization,
        "observe_python_facts",
        lambda _python: {"prefix": windows_spelling, "base_prefix": windows_spelling},
    )

    runtime_materialization.require_runtime_generation(target, args[4], args[5])

    monkeypatch.setattr(
        runtime_materialization,
        "observe_python_facts",
        lambda _python: {"prefix": r"D:\external", "base_prefix": r"D:\external"},
    )
    with pytest.raises(ValueError, match="hook_runtime_python_not_relocatable"):
        runtime_materialization.require_runtime_generation(target, args[4], args[5])


@pytest.mark.parametrize("available", [False, True])
def test_runtime_finalization_requires_python_but_not_a_console_launcher(
    tmp_path: Path, *, available: bool
) -> None:
    """Finalize only an interpreter-bearing generation and reclaim sealed output."""
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    if available:
        _write(runtime_materialization.runtime_python(runtime / "python"))
    artifact = PackageArtifact(tmp_path / "wheel", "c" * 64, runtime_build("a" * 40, "b" * 40))
    environment = _environment()
    files = runtime_materialization.runtime_file_inventory(runtime)
    target = tmp_path / runtime_digest(
        wheel_sha256=artifact.sha256,
        build=artifact.build,
        environment=environment,
        runtime_files=files,
    )
    expectation = (
        nullcontext()
        if available
        else pytest.raises(ValueError, match="hook_runtime_python_missing")
    )
    try:
        with expectation:
            vars(runtime_materialization)["_finalize_runtime"](
                runtime, target, artifact, environment, files
            )
        assert (runtime / "manifest.json").is_file() is available
    finally:
        runtime_materialization.remove_generated_tree(runtime, ignore_errors=True)


@pytest.mark.parametrize("fault", ["valid", "missing", "content", "encoding", "mode", "lock"])
def test_runtime_reuse_requires_current_supply_and_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """Repair predecessor payloads without mutating them or reprovisioning valid ones."""
    create_python = runtime_scenarios.create_fixture_python
    entry_fault = fault

    def with_entry(target, **kwargs):
        create_python(target, **kwargs)
        if entry_fault == "missing":
            (target / "bin/ethos").unlink(missing_ok=True)
            return
        payload = runtime_materialization.render_console_script("ethos").encode()
        if entry_fault in {"content", "encoding"}:
            payload = b"obsolete" if entry_fault == "content" else b"\xff"
        entry = _write(target / "bin/ethos", payload)
        entry.chmod(0o644 if entry_fault == "mode" else 0o755)

    monkeypatch.setattr(runtime_scenarios, "create_fixture_python", with_entry)
    repo, runtime = materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    selected = activate_runtime(common, runtime.parent)
    original = runtime_materialization.runtime_file_inventory(selected.root)
    digest = runtime_materialization.file_sha256
    if fault == "lock":
        monkeypatch.setattr(
            runtime_materialization,
            "file_sha256",
            lambda path: "e" * 64 if path == REPOSITORY_ROOT / "uv.lock" else digest(path),
        )

    invalid = fault == "lock" or (fault != "valid" and os.name != "nt")
    with monkeypatch.context() as probe:
        rebuild = Mock(side_effect=AssertionError("rebuild required"))
        probe.setattr(runtime_materialization, "require_python_image_source", rebuild)
        with pytest.raises(AssertionError, match="rebuild required") if invalid else nullcontext():
            reused = runtime_materialization.materialize_runtime(
                repo, Path(sys.executable), expected_build=selected.build
            )
            assert reused == selected.root / "python"
    if invalid and fault != "lock":
        entry_fault = "valid"
        repaired = runtime_materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=selected.build,
            build_source=REPOSITORY_ROOT,
        )
        assert repaired != runtime
        assert repaired.joinpath("bin/ethos").read_text() == (
            runtime_materialization.render_console_script("ethos")
        )
        activate_runtime(common, repaired.parent)
        assert (
            runtime_materialization.materialize_runtime(
                repo, Path(sys.executable), expected_build=selected.build
            )
            == repaired
        )
    assert runtime_materialization.runtime_file_inventory(selected.root) == original


@pytest.mark.parametrize("operation", ["seal", "remove"])
def test_runtime_mutation_rejects_hardlinks_without_changing_the_external_inode(
    tmp_path: Path,
    operation: str,
) -> None:
    external = tmp_path / "external"
    external.write_text("shared bytes\n", encoding="utf-8")
    external.chmod(0o644)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    try:
        os.link(external, runtime / "shared")
    except OSError as error:
        pytest.skip(f"hardlinks unavailable: {error}")

    effect = (
        vars(runtime_materialization)["_seal_runtime_payload"]
        if operation == "seal"
        else runtime_materialization.remove_generated_tree
    )
    with pytest.raises(ValueError, match="hook_runtime_generation_hardlink_invalid"):
        effect(runtime)

    assert stat.S_IMODE(external.stat().st_mode) == 0o644
    assert runtime.is_dir()


def test_install_rejects_nonexistent_and_relative_python(tmp_path: Path) -> None:
    for python in (Path("python"), tmp_path / "missing-python"):
        with pytest.raises(ValueError, match="hook_runtime_python_invalid"):
            hook_activation.install_hook_launchers(tmp_path, python=python)


def test_generated_tree_cleanup_rejects_a_junction_without_touching_its_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = tmp_path / "generated"
    junction = generated / "junction"
    junction.mkdir(parents=True)
    sentinel = junction / "sentinel"
    sentinel.write_text("outside authority\n", encoding="utf-8")
    with monkeypatch.context() as context:
        context.setattr(runtime_filesystem, "is_junction", lambda path: path == junction)
        with pytest.raises(ValueError, match="hook_runtime_generation_tree_invalid"):
            runtime_materialization.remove_generated_tree(generated)

    assert generated.is_dir()
    assert sentinel.read_text(encoding="utf-8") == "outside authority\n"
    runtime_materialization.remove_generated_tree(generated)
    failed = tmp_path / "failed"
    failed.mkdir()
    monkeypatch.setattr(
        runtime_materialization.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(OSError("busy")),
    )
    with pytest.raises(OSError, match="busy"):
        runtime_materialization.remove_generated_tree(failed)
    runtime_materialization.remove_generated_tree(failed, ignore_errors=True)
