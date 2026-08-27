"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
import ethos.adapters.repo.runtime.materialization.python_image as runtime_python_image
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import runtime_environment
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.transition import ReleaseArtifact
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import runtime_build


def _environment(**changes: str):
    values = {"python_abi": "cpython-test", "python_version": "3.14.7",
              "python_implementation": "cpython", "dependency_lock_sha256": "d" * 64,
              "platform_name": "test", "architecture_name": "test-architecture"}
    return runtime_environment(**(values | changes))


def _python_facts(home: Path) -> dict[str, str]:
    return {"python_abi": "cpython-test", "python_version": "3.14.7",
            "python_implementation": "cpython", "architecture": "test-architecture",
            "prefix": home.as_posix(), "base_prefix": home.as_posix()}


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
    artifact = ReleaseArtifact(wheel, "c" * 64, runtime_build("a" * 40, "b" * 40))

    def materialize_python(target: Path, *_args: object, **_kwargs: object) -> None:
        for relative, payload in (("bin/python", b"python"), ("bin/ethos", b"ethos")):
            _write(target / relative, payload)

    observed: list[Path] = []
    inventory = runtime_materialization.runtime_file_inventory
    monkeypatch.setattr(runtime_materialization, "materialize_python_image", materialize_python)
    monkeypatch.setattr(runtime_materialization, "runtime_file_inventory",
                        lambda root: observed.append(root) or inventory(root))
    monkeypatch.setattr(runtime_materialization, "observe_python_facts",
                        lambda python: {"prefix": python.parent.parent.resolve().as_posix(),
                                        "base_prefix": python.parent.parent.resolve().as_posix()})
    monkeypatch.setattr(runtime_materialization.subprocess, "run",
                        lambda *_a, **_k: subprocess.CompletedProcess([], 0, "0.2.0-alpha.1\n", ""))
    return (runtime_root, work, source, interpreter, artifact, _environment()), observed


def test_materialized_python_is_a_product_owned_non_mutating_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "managed-python"
    interpreter = _write(home / "bin/python3.14", b"python-runtime")
    interpreter.chmod(0o755)
    for relative in ("lib/python3.14/os.py", "lib/python3.14/test/support.py",
                     "include/Python.h", "share/python.1"):
        _write(home / relative)
    target = tmp_path / "runtime/python"
    monkeypatch.setattr(runtime_python_image, "observe_python_facts",
                        lambda _python: _python_facts(home))

    def install(
        _source: Path,
        _work: Path,
        python: Path,
        _wheel: Path,
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
        target, tmp_path, interpreter, tmp_path / "ethos.whl", tmp_path / "work", locked=True)

    assert (target / "bin/python").read_bytes() == b"python-runtime"
    assert not any((target / path).exists() for path in
                   ("include", "share", "lib/python3.14/test"))
    assert not tuple(target.rglob("__pycache__")) + tuple(target.rglob("*.pyc"))
    for name in ("ethos", "uv"):
        script = target / "bin" / name
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
    target = runtime_materialization.materialize_runtime_generation(*args, locked=False)

    assert len(observed) == 2
    assert observed[0].name.startswith(".runtime-build-")
    assert observed[1] == target
    assert stat.S_IMODE(target.stat().st_mode) & 0o222 == 0
    assert stat.S_IMODE((target / "manifest.json").stat().st_mode) & 0o222 == 0
    assert all(
        path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o222 == 0
        for path in target.rglob("*")
    )
    assert runtime_materialization.materialize_runtime_generation(*args, locked=False) == target
    is_dir = Path.is_dir
    mode = stat.S_IMODE(runtime_root.stat().st_mode)
    runtime_root.chmod(mode | stat.S_IWUSR)
    with monkeypatch.context() as context:
        seen: set[Path] = set()
        context.setattr(Path, "is_dir", lambda path: is_dir(path)
                        if path != target or path in seen else bool(seen.add(path)))
        context.setattr(
            Path, "rename", lambda _path, _target: (_ for _ in ()).throw(FileExistsError)
        )
        assert runtime_materialization.materialize_runtime_generation(*args, locked=False) == target
    runtime_root.chmod(mode)
    with monkeypatch.context() as context:
        context.setattr(runtime_materialization, "runtime_file_inventory", lambda _root: {})
        with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
            runtime_materialization.require_runtime_generation(target, args[4], environment)
    with monkeypatch.context() as context:
        context.setattr(runtime_materialization, "observe_python_facts",
                        lambda _python: {"prefix": "wrong", "base_prefix": "wrong"})
        with pytest.raises(ValueError, match="hook_runtime_python_not_relocatable"):
            runtime_materialization.require_runtime_generation(target, args[4], environment)
    monkeypatch.setattr(runtime_materialization.subprocess, "run",
                        lambda *_a, **_k: subprocess.CompletedProcess([], 1, "", "failed"))
    with pytest.raises(ValueError, match="hook_runtime_entrypoint_smoke_failed"):
        runtime_materialization.materialize_runtime_generation(
            *args[:-1], _environment(architecture_name="other"), locked=False)
    assert {path for path in runtime_root.iterdir() if path.is_dir()} == {target}


@pytest.mark.parametrize(("missing", "reason"), [("python", "python"), ("ethos", "entrypoint")])
def test_runtime_finalization_requires_python_and_entrypoint(
    tmp_path: Path, missing: str, reason: str
) -> None:
    runtime = tmp_path / missing
    for path in (runtime_materialization.runtime_python(runtime / "python"),
                 runtime_materialization.runtime_entrypoint(runtime / "python")):
        _write(path)
    (runtime / "python/bin" / missing).unlink()
    artifact = ReleaseArtifact(tmp_path / "wheel", "c" * 64, runtime_build("a" * 40, "b" * 40))
    with pytest.raises(ValueError, match=f"hook_runtime_{reason}_missing"):
        vars(runtime_materialization)["_finalize_runtime"](
            runtime, tmp_path / "digest", artifact, _environment(), {})


def test_runtime_reuse_rejects_architecture_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    selected = activate_runtime(Path(git_common_dir(repo)), venv.parent)
    drifted = runtime_environment(python_abi=selected.python_abi,
        python_version=selected.python_version,
        python_implementation=selected.python_implementation,
        dependency_lock_sha256=selected.dependency_lock_sha256, platform_name=selected.platform,
        architecture_name="x86_64" if selected.architecture != "x86_64" else "arm64")
    monkeypatch.setattr(runtime_materialization, "resolve_owned_interpreter",
                        lambda *_args: selected.python)
    monkeypatch.setattr(runtime_materialization, "observe_runtime_environment",
                        lambda *_args, **_kwargs: drifted)

    def rebuild_required(*_args: object) -> Path:
        message = "architecture rebuild required"
        raise RuntimeError(message)

    monkeypatch.setattr(runtime_materialization, "resolve_runtime_wheel", rebuild_required)

    with pytest.raises(RuntimeError, match="architecture rebuild required"):
        runtime_materialization.materialize_runtime(repo, selected.python,
                                                    expected_build=selected.build)


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
    monkeypatch.setattr(runtime_materialization.shutil, "rmtree",
                        lambda _path: (_ for _ in ()).throw(OSError("busy")))
    with pytest.raises(OSError, match="busy"):
        runtime_materialization.remove_generated_tree(failed)
    runtime_materialization.remove_generated_tree(failed, ignore_errors=True)
