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


def test_materialized_python_is_a_product_owned_non_mutating_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "managed-python"
    interpreter = home / "bin/python3.14"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_bytes(b"python-runtime")
    interpreter.chmod(0o755)
    stdlib = home / "lib/python3.14"
    stdlib.mkdir(parents=True)
    (stdlib / "os.py").write_text("# stdlib\n", encoding="utf-8")
    (stdlib / "test").mkdir()
    (stdlib / "test/support.py").write_text("# test-only\n", encoding="utf-8")
    (home / "include").mkdir()
    (home / "include/Python.h").write_text("/* build-only */\n", encoding="utf-8")
    (home / "share").mkdir()
    (home / "share/python.1").write_text("manual\n", encoding="utf-8")
    target = tmp_path / "runtime/python"

    monkeypatch.setattr(
        runtime_python_image,
        "observe_python_facts",
        lambda _python: {
            "python_abi": "cpython-test",
            "python_version": "3.14.7",
            "python_implementation": "cpython",
            "architecture": "test-architecture",
            "prefix": home.as_posix(),
            "base_prefix": home.as_posix(),
        },
    )

    def install(
        _source: Path,
        _work: Path,
        python: Path,
        _wheel: Path,
    ) -> None:
        scripts = python.parent
        for name in ("ethos", "uv"):
            script = scripts / name
            script.write_text(
                f"#!{target}/staging-python\nprint({name!r})\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
        cache = target / "lib/python3.14/site-packages/ethos/__pycache__"
        cache.mkdir(parents=True)
        (cache / "module.cpython-314.pyc").write_bytes(b"bytecode")

    monkeypatch.setattr(runtime_python_image, "install_locked_runtime", install)
    monkeypatch.setattr(
        runtime_python_image,
        "console_script_entries",
        lambda _python: {"ethos": "ethos.cli:main", "uv": "uv:main"},
        raising=False,
    )

    materialize_python = runtime_python_image.materialize_python_image
    materialize_python(
        target,
        tmp_path,
        interpreter,
        tmp_path / "ethos.whl",
        tmp_path / "work",
        locked=True,
    )

    assert (target / "bin/python").read_bytes() == b"python-runtime"
    assert not (target / "include").exists()
    assert not (target / "share").exists()
    assert not (target / "lib/python3.14/test").exists()
    assert not tuple(target.rglob("__pycache__"))
    assert not tuple(target.rglob("*.pyc"))
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
    runtime_root = tmp_path / "runtime"
    work = runtime_root / ".work"
    source = tmp_path / "source"
    interpreter = tmp_path / "python"
    wheel = tmp_path / "ethos.whl"
    source.mkdir()
    interpreter.write_bytes(b"python")
    wheel.write_bytes(b"wheel")
    build = runtime_build("a" * 40, "b" * 40)
    artifact = ReleaseArtifact(wheel, "c" * 64, build)
    environment = runtime_environment(
        python_abi="cpython-test",
        python_version="3.14.7",
        python_implementation="cpython",
        dependency_lock_sha256="d" * 64,
        platform_name="test",
        architecture_name="test-architecture",
    )

    def materialize_python(
        target: Path,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        binary = target / "bin/python"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"python")
        entrypoint = target / "bin/ethos"
        entrypoint.write_bytes(b"ethos")

    observed: list[Path] = []
    inventory = runtime_materialization.runtime_file_inventory

    def record_inventory(root: Path) -> dict[str, str]:
        observed.append(root)
        return inventory(root)

    monkeypatch.setattr(runtime_materialization, "materialize_python_image", materialize_python)
    monkeypatch.setattr(runtime_materialization, "runtime_file_inventory", record_inventory)
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
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "0.2.0-alpha.1\n", ""),
    )

    target = runtime_materialization.materialize_runtime_generation(
        runtime_root,
        work,
        source,
        interpreter,
        artifact,
        environment,
        locked=False,
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
        runtime_materialization,
        "resolve_owned_interpreter",
        lambda *_args: selected.python,
    )
    monkeypatch.setattr(
        runtime_materialization,
        "observe_runtime_environment",
        lambda *_args, **_kwargs: drifted,
    )

    def rebuild_required(*_args: object) -> Path:
        message = "architecture rebuild required"
        raise RuntimeError(message)

    monkeypatch.setattr(runtime_materialization, "resolve_runtime_wheel", rebuild_required)

    with pytest.raises(RuntimeError, match="architecture rebuild required"):
        runtime_materialization.materialize_runtime(
            repo,
            selected.python,
            expected_build=selected.build,
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
        runtime_materialization._seal_runtime_payload  # noqa: SLF001
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


def test_install_rejects_unavailable_source_authority_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    python = tmp_path / "python"
    python.write_text("python", encoding="utf-8")
    materialized = False

    def unavailable(_root: Path):
        message = "hook_runtime_accepted_build_identity_unavailable"
        raise ValueError(message)

    def materialize(*_args: object, **_kwargs: object) -> Path:
        nonlocal materialized
        materialized = True
        return tmp_path / "runtime/python"

    monkeypatch.setattr(hook_activation, "expected_runtime_build", unavailable)
    monkeypatch.setattr(hook_activation.runtime_materialization, "materialize_runtime", materialize)

    with pytest.raises(ValueError, match="hook_runtime_accepted_build_identity_unavailable"):
        hook_activation.install_hook_launchers(tmp_path, python=python)

    assert materialized is False


def test_generated_tree_cleanup_rejects_a_junction_without_touching_its_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = tmp_path / "generated"
    junction = generated / "junction"
    junction.mkdir(parents=True)
    sentinel = junction / "sentinel"
    sentinel.write_text("outside authority\n", encoding="utf-8")
    monkeypatch.setattr(
        runtime_filesystem,
        "is_junction",
        lambda path: path == junction,
    )

    with pytest.raises(ValueError, match="hook_runtime_generation_tree_invalid"):
        runtime_materialization.remove_generated_tree(generated)

    assert generated.is_dir()
    assert sentinel.read_text(encoding="utf-8") == "outside authority\n"
