"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
import ethos.adapters.repo.runtime.materialization.python_image as runtime_python_image
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_environment
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.transition import PackageArtifact
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
    return {
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


def test_ordinary_wheel_install_materializes_the_embedded_locked_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert (
        subprocess.run(
            ("git", "init", "--quiet", "--initial-branch=dev"),
            cwd=repo,
            check=False,
        ).returncode
        == 0
    )
    package_source = tmp_path / "bootstrap/lib/python3.14"
    module = package_source / "site-packages/ethos/adapters/repo/runtime/materialization/effect.py"
    project = tmp_path / "embedded-runtime-project"
    interpreter = _write(tmp_path / "managed-python/bin/python", b"python")
    wheel = _write(tmp_path / "ethos.whl", b"wheel")
    requirements = _write(tmp_path / "locked-requirements.txt", b"package==1\n")
    cache = tmp_path / "shared-uv-cache"
    identity = runtime_build("a" * 40, "b" * 40)
    environment = _environment()
    observed: dict[str, object] = {}

    monkeypatch.setenv("UV_CACHE_DIR", cache.as_posix())
    monkeypatch.setattr(runtime_materialization, "__file__", module.as_posix())
    monkeypatch.setattr(runtime_materialization, "resolve_runtime_project", lambda _root: project)
    monkeypatch.setattr(
        runtime_materialization,
        "resolve_owned_interpreter",
        lambda _source, _python: interpreter,
    )
    monkeypatch.setattr(runtime_materialization, "observe_python_facts", lambda _python: {})
    monkeypatch.setattr(
        runtime_materialization,
        "observe_runtime_environment",
        lambda *_args, **_kwargs: environment,
    )
    monkeypatch.setattr(runtime_materialization, "_reusable_runtime", lambda *_args: None)
    monkeypatch.setattr(
        runtime_materialization,
        "is_selected_runtime_source",
        lambda _source: False,
    )

    def resolve_wheel(source: Path, _wheel_dir: Path, **_kwargs: object) -> Path:
        observed["source"] = source
        observed["wheel_cache"] = _kwargs["cache_dir"]
        return wheel

    monkeypatch.setattr(runtime_materialization, "resolve_runtime_wheel", resolve_wheel)

    def prepare(
        source: Path,
        _work: Path,
        selected_interpreter: Path,
        **_kwargs: object,
    ) -> Path:
        observed["prepared"] = (source, selected_interpreter)
        observed["requirements_cache"] = _kwargs["cache_dir"]
        return requirements

    monkeypatch.setattr(runtime_materialization, "prepare_locked_requirements", prepare)
    monkeypatch.setattr(
        runtime_materialization,
        "materialize_package_wheel",
        lambda *_args, **_kwargs: PackageArtifact(wheel, "c" * 64, identity),
    )

    def materialize_generation(*_args: object, **kwargs: object) -> Path:
        observed["locked_requirements"] = kwargs["locked_requirements"]
        observed["generation_cache"] = kwargs["cache_dir"]
        return tmp_path / "runtime-generation"

    monkeypatch.setattr(
        runtime_materialization,
        "materialize_runtime_generation",
        materialize_generation,
    )

    runtime = runtime_materialization.materialize_runtime(
        repo,
        interpreter,
        expected_build=identity,
    )

    assert observed["source"] == package_source
    assert observed["prepared"] == (project, interpreter)
    assert observed["wheel_cache"] == cache
    assert observed["requirements_cache"] == cache
    assert observed["generation_cache"] == cache
    assert observed["locked_requirements"] == requirements
    assert runtime == tmp_path / "runtime-generation/python"


def test_materialized_python_is_a_product_owned_non_mutating_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "managed-python"
    interpreter = _write(home / "bin/python3.14", b"python-runtime")
    interpreter.chmod(0o755)
    for relative in (
        "lib/python3.14/os.py",
        "lib/python3.14/test/support.py",
        "include/Python.h",
        "share/python.1",
    ):
        _write(home / relative)
    target = tmp_path / "runtime/python"
    monkeypatch.setattr(
        runtime_python_image, "observe_python_facts", lambda _python: _python_facts(home)
    )

    def install(
        _source: Path,
        python: Path,
        _wheel: Path,
        _requirements: Path,
        **_kwargs: object,
    ) -> None:
        scripts = python.parent
        for name in ("ethos", "uv"):
            payload = f"#!{target}/staging-python\nprint({name!r})\n".encode()
            script = _write(scripts / name, payload)
            script.chmod(0o755)
        _write(target / "lib/python3.14/site-packages/ethos/__pycache__/module.pyc")

    monkeypatch.setattr(runtime_python_image, "install_locked_runtime", install)
    monkeypatch.setattr(
        runtime_python_image,
        "console_script_entries",
        lambda _python: {"ethos": "ethos.cli:main", "uv": "uv:main"},
        raising=False,
    )

    runtime_python_image.materialize_python_image(
        target,
        tmp_path,
        interpreter,
        tmp_path / "ethos.whl",
        locked_requirements=tmp_path / "requirements.txt",
    )

    assert (target / "bin/python").read_bytes() == b"python-runtime"
    assert not any((target / path).exists() for path in ("include", "share", "lib/python3.14/test"))
    assert not tuple(target.rglob("__pycache__")) + tuple(target.rglob("*.pyc"))
    assert not (target / "bin/ethos").exists()
    script = target / "bin/uv"
    text = script.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh\n")
    assert " -B -I " in text
    assert target.as_posix() not in text


def test_runtime_generation_hashes_only_prepared_and_exposed_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, observed = _generation_case(tmp_path, monkeypatch)
    runtime_root, *_, environment = args
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
            *args[:-1],
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
    monkeypatch.setattr(runtime_materialization, "os", SimpleNamespace(name="nt"))
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
    commands: list[tuple[object, ...]] = []

    def run(command: tuple[object, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
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


def test_runtime_reuse_rejects_architecture_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    selected = activate_runtime(Path(git_common_dir(repo)), venv.parent)
    drifted = runtime_environment(
        python_abi=selected.python_abi,
        python_version=selected.python_version,
        python_implementation=selected.python_implementation,
        dependency_lock_sha256=selected.dependency_lock_sha256,
        platform_name=selected.platform,
        architecture_name="x86_64" if selected.architecture != "x86_64" else "arm64",
    )
    monkeypatch.setattr(
        runtime_materialization, "resolve_owned_interpreter", lambda *_args: selected.python
    )
    monkeypatch.setattr(
        runtime_materialization, "observe_runtime_environment", lambda *_args, **_kwargs: drifted
    )

    def rebuild_required(*_args: object, **_kwargs: object) -> Path:
        message = "architecture rebuild required"
        raise RuntimeError(message)

    monkeypatch.setattr(runtime_materialization, "resolve_runtime_wheel", rebuild_required)

    with pytest.raises(RuntimeError, match="architecture rebuild required"):
        runtime_materialization.materialize_runtime(
            repo, selected.python, expected_build=selected.build
        )


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
