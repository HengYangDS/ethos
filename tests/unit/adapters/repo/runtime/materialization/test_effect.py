"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
import ethos.adapters.repo.runtime.materialization.python_environment as runtime_python_environment
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
    executable = home / "bin/python"
    return {
        "executable": executable.resolve().as_posix(),
        "base_executable": executable.resolve().as_posix(),
        "python_abi": "cpython-test",
        "python_version": "3.14.7",
        "python_implementation": "cpython",
        "architecture": "test-architecture",
        "prefix": home.as_posix(),
        "base_prefix": home.as_posix(),
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
    monkeypatch.setattr(runtime_materialization, "materialize_python_image", materialize_python)
    monkeypatch.setattr(
        runtime_materialization,
        "runtime_file_inventory",
        lambda root: observed.append(root) or inventory(root),
    )
    monkeypatch.setattr(
        runtime_materialization,
        "observe_python_facts",
        lambda python: {
            "prefix": python.parent.parent.resolve().as_posix(),
            "base_prefix": python.parent.parent.resolve().as_posix(),
        },
    )
    monkeypatch.setattr(
        runtime_materialization.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess([], 0, "0.2.0-alpha.2\n", ""),
    )
    return (runtime_root, work, source, interpreter, artifact, _environment()), observed


@pytest.mark.parametrize("supply", ["packaged", "split-image", "source", "selected"])
def test_runtime_materialization_binds_package_dependency_and_image_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, supply: str
) -> None:
    """Package, source, and selected-runtime supply preserve their own coordinates."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(("git", "init", "--quiet", "--initial-branch=dev"), cwd=repo, check=True)
    package = tmp_path / "bootstrap/lib/python3.14"
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
        "__file__": str(
            package / "site-packages/ethos/adapters/repo/runtime/materialization/effect.py"
        ),
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
    args, observed = _generation_case(tmp_path, monkeypatch)
    runtime_root, work, source, interpreter, artifact, environment = args
    target = runtime_materialization.materialize_runtime_generation(*args, locked_requirements=None)

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
    monkeypatch.setattr(
        runtime_materialization.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess([], 7, "out", "failed"),
    )
    with pytest.raises(
        ValueError,
        match=(
            r"hook_runtime_module_smoke_failed:command=.*python -B -I -m ethos\.cli "
            "--version:returncode=7:stdout=out:stderr=failed"
        ),
    ):
        runtime_materialization.materialize_runtime_generation(
            runtime_root,
            work,
            source,
            interpreter,
            artifact,
            _environment(architecture_name="other"),
            locked_requirements=None,
        )
    assert {path for path in runtime_root.iterdir() if path.is_dir()} == {target}


def test_runtime_generation_compares_windows_prefixes_as_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, _observed = _generation_case(tmp_path, monkeypatch)
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


def test_runtime_generation_smoke_uses_the_authenticated_python_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, _observed = _generation_case(tmp_path, monkeypatch)
    commands: list[tuple[Path | str, ...]] = []

    def run(command: tuple[Path | str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "0.2.0-alpha.3\n", "")

    monkeypatch.setattr(runtime_materialization.subprocess, "run", run)

    target = runtime_materialization.materialize_runtime_generation(*args, locked_requirements=None)

    assert commands == [
        (
            runtime_materialization.runtime_python(target / "python"),
            "-B",
            "-I",
            "-m",
            "ethos.cli",
            "--version",
        )
    ]


def test_runtime_finalization_does_not_require_a_generated_ethos_launcher(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
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

    try:
        vars(runtime_materialization)["_finalize_runtime"](
            runtime,
            target,
            artifact,
            environment,
            files,
        )
        assert (runtime / "manifest.json").is_file()
    finally:
        runtime_materialization.remove_generated_tree(runtime, ignore_errors=True)


def test_runtime_finalization_requires_python(tmp_path: Path) -> None:
    runtime = tmp_path / "missing-python"
    runtime.mkdir()
    artifact = PackageArtifact(tmp_path / "wheel", "c" * 64, runtime_build("a" * 40, "b" * 40))
    with pytest.raises(ValueError, match="hook_runtime_python_missing"):
        vars(runtime_materialization)["_finalize_runtime"](
            runtime, tmp_path / "digest", artifact, _environment(), {}
        )


def test_runtime_reuse_rejects_dependency_lock_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    selected = activate_runtime(Path(git_common_dir(repo)), venv.parent)
    drifted_lock = "e" * 64
    drifted = runtime_environment(
        python_abi=selected.python_abi,
        python_version=selected.python_version,
        python_implementation=selected.python_implementation,
        dependency_lock_sha256=drifted_lock,
        platform_name=selected.platform,
        architecture_name=selected.architecture,
    )
    digest = runtime_materialization.file_sha256
    monkeypatch.setattr(
        runtime_materialization,
        "file_sha256",
        lambda path: drifted_lock if path == REPOSITORY_ROOT / "uv.lock" else digest(path),
    )
    monkeypatch.setattr(
        runtime_materialization,
        "require_python_image_source",
        lambda _python: {
            "executable": selected.python.resolve().as_posix(),
            "base_executable": selected.python.resolve().as_posix(),
            "python_abi": selected.python_abi,
            "python_version": selected.python_version,
            "python_implementation": selected.python_implementation,
            "architecture": selected.architecture,
            "prefix": selected.python.parent.parent.resolve().as_posix(),
            "base_prefix": selected.python.parent.parent.resolve().as_posix(),
        },
    )
    monkeypatch.setattr(
        runtime_materialization, "observe_runtime_environment", lambda *_args, **_kwargs: drifted
    )
    requirements = _write(tmp_path / "locked-requirements.txt", b"fixture==1\n")
    monkeypatch.setattr(
        runtime_materialization,
        "prepare_locked_requirements",
        lambda *_args, **_kwargs: requirements,
    )

    def rebuild_required(*_args: object, **_kwargs: object) -> Path:
        message = "dependency-lock rebuild required"
        raise RuntimeError(message)

    monkeypatch.setattr(runtime_materialization, "resolve_runtime_wheel", rebuild_required)

    with pytest.raises(RuntimeError, match="dependency-lock rebuild required"):
        runtime_materialization.materialize_runtime(
            repo, selected.python, expected_build=selected.build
        )


def test_runtime_reuse_does_not_require_a_new_python_image_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, runtime = materialize_runtime_case(tmp_path, monkeypatch)
    selected = activate_runtime(Path(git_common_dir(repo)), runtime.parent)

    def image_source_not_needed(_python: Path) -> dict[str, str]:
        msg = "existing runtime should be selected before provisioning"
        raise AssertionError(msg)

    monkeypatch.setattr(
        runtime_materialization,
        "require_python_image_source",
        image_source_not_needed,
    )

    reused = runtime_materialization.materialize_runtime(
        repo,
        Path(sys.executable),
        expected_build=selected.build,
    )

    assert reused == selected.root / "python"


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
