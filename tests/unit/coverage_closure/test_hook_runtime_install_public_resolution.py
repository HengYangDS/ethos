"""Immutable hook-runtime installation resolution boundaries."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.hook_runtime_install as install
import ethos.adapters.repo.runtime.transition as identity_transition
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_environment
from ethos.repository.release.identity import BuildIdentity

_BUILD_IDENTITY = BuildIdentity(
    product_version="0.2.0-alpha.1",
    distribution_version="0.2.0a1.dev0+gaaaaaaaaaaaa.tbbbbbbbbbbbb",
    source_commit="a" * 40,
    source_tree="b" * 40,
    channel="development",
    acceptance_state="unaccepted",
)
_ENVIRONMENT = runtime_environment(
    python_abi="cpython-test",
    python_version="3.14.7",
    python_implementation="cpython",
    dependency_lock_sha256="d" * 64,
    platform_name=platform.system().lower(),
)


def _bind_build_identity(monkeypatch: pytest.MonkeyPatch) -> BuildIdentity:
    monkeypatch.setattr(
        identity_transition,
        "wheel_build_identity",
        lambda _wheel: _BUILD_IDENTITY,
    )
    return _BUILD_IDENTITY


def _completed(code: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess((), code, stdout, stderr)


def _managed_runtime_case(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    wheel_sha256 = hashlib.sha256(b"wheel").hexdigest()
    runtime = tmp_path / "repo.git/ethos/runtime" / ("a" * 64)
    source = runtime / "python/lib/python3.14/site-packages"
    source.mkdir(parents=True)
    monkeypatch.setattr(sys, "prefix", (runtime / "python").as_posix())
    monkeypatch.setattr(
        install,
        "require_selected_runtime",
        lambda candidate: (
            type("Selected", (), {"wheel_sha256": wheel_sha256})() if candidate == runtime else None
        ),
    )
    return source, tmp_path / "repo.git/ethos/packages" / wheel_sha256


@pytest.mark.parametrize("wheel_count", [0, 2])
def test_source_wheel_resolution_requires_exactly_one_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, wheel_count: int
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    wheel_dir = tmp_path / "build/wheel"
    python = tmp_path / "bin/python"
    uv = python.with_name("uv")
    uv.parent.mkdir(parents=True)
    uv.write_text("tool", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", python.as_posix())

    commands: list[tuple[str, ...]] = []

    def build(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[1] == "build":
            output = Path(command[-1])
            output.mkdir(parents=True, exist_ok=True)
            for index in range(wheel_count):
                (output / f"ethos-{index}.whl").write_bytes(b"wheel")
        return _completed(0)

    monkeypatch.setattr(install.subprocess, "run", build)
    with pytest.raises(ValueError, match="hook_runtime_wheel_invalid"):
        install.resolve_runtime_wheel(source, wheel_dir)
    assert commands[0][1:] == ("sync", "--locked", "--offline", "--check", "--active")
    assert "--no-build-isolation" in commands[1]


def test_installed_wheel_resolution_rejects_missing_and_non_file_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = type("Metadata", (), {"read_text": lambda *_args: None})()
    monkeypatch.setattr(install, "distribution", lambda _name: missing)
    with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
        install.resolve_runtime_wheel(tmp_path, tmp_path / "wheel")

    metadata = type(
        "Metadata",
        (),
        {"read_text": lambda *_args: json.dumps({"url": "https://example.test/ethos.whl"})},
    )()
    monkeypatch.setattr(install, "distribution", lambda _name: metadata)
    with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
        install.resolve_runtime_wheel(tmp_path, tmp_path / "wheel")


def test_installed_wheel_resolution_accepts_exact_file_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wheel = tmp_path / "ethos.whl"
    wheel.write_bytes(b"wheel")
    metadata = type(
        "Metadata",
        (),
        {"read_text": lambda *_args: json.dumps({"url": wheel.as_uri()})},
    )()
    monkeypatch.setattr(install, "distribution", lambda _name: metadata)

    assert install.resolve_runtime_wheel(tmp_path / "installed", tmp_path / "unused") == wheel


def test_managed_runtime_resolves_its_git_common_content_addressed_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, package_root = _managed_runtime_case(monkeypatch, tmp_path)
    wheel = package_root / "ethos-test.whl"
    wheel.parent.mkdir(parents=True)
    wheel.write_bytes(b"wheel")

    assert install.resolve_runtime_wheel(source, tmp_path / "unused") == wheel


def test_managed_runtime_rejects_missing_or_ambiguous_content_addressed_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, package_root = _managed_runtime_case(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
        install.resolve_runtime_wheel(source, tmp_path / "unused")

    package_root.mkdir(parents=True)
    (package_root / "ethos-drifted.whl").write_bytes(b"drifted")
    with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
        install.resolve_runtime_wheel(source, tmp_path / "unused")

    (package_root / "ethos-drifted.whl").unlink()
    for name in ("ethos-first.whl", "ethos-second.whl"):
        (package_root / name).write_bytes(b"wheel")
    with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
        install.resolve_runtime_wheel(source, tmp_path / "unused")


def test_owned_python_copy_rejects_interpreter_outside_its_base_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    interpreter = tmp_path / "foreign/python"
    interpreter.parent.mkdir()
    interpreter.write_bytes(b"python")
    monkeypatch.setattr(
        install,
        "python_facts",
        lambda _python: {
            "python_abi": "cpython-test",
            "python_version": "3.14.7",
            "python_implementation": "cpython",
            "prefix": (tmp_path / "prefix").as_posix(),
            "base_prefix": (tmp_path / "base").as_posix(),
        },
    )

    with pytest.raises(ValueError, match="hook_runtime_owned_interpreter_unavailable"):
        install.copy_python_home(interpreter, tmp_path / "target")


def test_runtime_tool_reports_missing_executable_and_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    missing_wheel_dir = tmp_path / "missing" / "wheel"
    monkeypatch.setattr(sys, "executable", (tmp_path / "bin/python").as_posix())
    with pytest.raises(ValueError, match="hook_runtime_uv_unavailable"):
        install.resolve_runtime_wheel(source, missing_wheel_dir)

    uv = tmp_path / "bin/uv"
    uv.parent.mkdir(parents=True)
    uv.write_text("tool", encoding="utf-8")
    monkeypatch.setattr(
        install.subprocess,
        "run",
        lambda *_args, **_kwargs: _completed(1, stderr="build failed"),
    )
    failed_wheel = tmp_path / "failed" / "wheel"
    with pytest.raises(ValueError, match="build failed"):
        install.resolve_runtime_wheel(source, failed_wheel)
    assert not failed_wheel.exists()

    def build(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[1] == "build":
            output = Path(command[-1])
            output.mkdir(parents=True)
            (output / "ethos-retry.whl").write_bytes(b"wheel")
        return _completed(0)

    monkeypatch.setattr(install.subprocess, "run", build)
    assert install.resolve_runtime_wheel(source, failed_wheel).parent == failed_wheel


def test_source_wheel_resolution_rejects_a_drifted_bootstrap_environment_before_writing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    python = tmp_path / "bin/python"
    uv = python.with_name("uv")
    uv.parent.mkdir(parents=True)
    uv.write_text("tool", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", python.as_posix())
    commands: list[tuple[str, ...]] = []

    def reject(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return _completed(1, stderr="source environment drift")

    monkeypatch.setattr(install.subprocess, "run", reject)
    wheel_dir = tmp_path / "build/wheel"

    with pytest.raises(ValueError, match="source environment drift"):
        install.resolve_runtime_wheel(source, wheel_dir)

    assert commands == [(uv.as_posix(), "sync", "--locked", "--offline", "--check", "--active")]
    assert not wheel_dir.parent.exists()


def test_python_abi_and_manifest_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    python = tmp_path / "python"
    python.write_bytes(b"python")
    monkeypatch.setattr(install.subprocess, "run", lambda *_args, **_kwargs: _completed(1))
    with pytest.raises(ValueError, match="hook_runtime_python_abi_invalid"):
        install.python_facts(python)

    supply = install.runtime_supply(
        mode="locked-source",
        source=tmp_path,
        wheel=tmp_path / "ethos.whl",
        interpreter=python,
    )
    monkeypatch.setattr(
        install,
        "copy_python_home",
        lambda _source, target: target.mkdir(parents=True),
    )
    with pytest.raises(ValueError, match="hook_runtime_python_missing"):
        install.materialize_runtime_python(tmp_path / "runtime/python", supply, tmp_path)


def test_owned_python_copy_copies_the_complete_interpreter_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prefix = tmp_path / "prefix"
    python = prefix / "bin/python"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"python")
    monkeypatch.setattr(
        install,
        "python_facts",
        lambda _python: {
            "python_abi": "cpython-test",
            "python_version": "3.14.7",
            "python_implementation": "cpython",
            "prefix": prefix.as_posix(),
            "base_prefix": prefix.as_posix(),
        },
    )

    runtime = tmp_path / "runtime/python"
    install.copy_python_home(python, runtime)

    assert (runtime / "bin/python").read_bytes() == b"python"
    assert not (runtime / "bin/python").is_symlink()


def test_materialize_runtime_installs_from_durable_content_addressed_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _bind_build_identity(monkeypatch)
    source = tmp_path / "source"
    module = source / "a/b/c/d/module.py"
    module.parent.mkdir(parents=True)
    (source / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    volatile_wheel = tmp_path / "volatile/ethos-test.whl"
    volatile_wheel.parent.mkdir()
    volatile_wheel.write_bytes(b"wheel")
    wheel_sha256 = hashlib.sha256(b"wheel").hexdigest()
    common = tmp_path / "repo.git"
    common.mkdir()
    calls: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(identity_transition, "git_common_dir", lambda _repo: common.as_posix())

    def run_runtime_tool(_source: Path, operation: str, *args: str) -> None:
        calls.append((operation, args))

    monkeypatch.setattr(install, "_run_runtime_tool", run_runtime_tool)
    artifact = identity_transition.materialize_release_wheel(
        tmp_path / "repo",
        volatile_wheel,
        expected_build=_BUILD_IDENTITY,
        collision="hook_runtime_wheel_digest_collision",
    )
    install.install_locked_runtime(source, tmp_path / "work", tmp_path / "python", artifact.path)
    volatile_wheel.unlink()

    durable = common / "ethos/packages" / wheel_sha256 / volatile_wheel.name
    assert calls[0][1][:4] == ("--locked", "--offline", "--no-dev", "--no-emit-project")
    assert calls[1][0] == "pip"
    assert {"sync", "--offline", "--break-system-packages", "--require-hashes"} < set(calls[1][1])
    assert calls[2][0] == "pip"
    assert {"install", "--offline", "--break-system-packages", "--no-deps"} < set(calls[2][1])
    assert Path(calls[2][1][-1]) == durable
    assert durable.read_bytes() == b"wheel"


def test_materialize_runtime_rejects_durable_wheel_digest_collision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _bind_build_identity(monkeypatch)
    source = tmp_path / "installed/a/b/c/d"
    source.mkdir(parents=True)
    wheel = tmp_path / "ethos-test.whl"
    wheel.write_bytes(b"wheel")
    wheel_sha256 = hashlib.sha256(b"wheel").hexdigest()
    common = tmp_path / "repo.git"
    durable = common / "ethos/packages" / wheel_sha256 / wheel.name
    durable.parent.mkdir(parents=True)
    durable.write_bytes(b"different")
    monkeypatch.setattr(identity_transition, "git_common_dir", lambda _repo: common.as_posix())

    with pytest.raises(ValueError, match="hook_runtime_wheel_digest_collision"):
        identity_transition.materialize_release_wheel(
            tmp_path / "repo",
            wheel,
            expected_build=_BUILD_IDENTITY,
            collision="hook_runtime_wheel_digest_collision",
        )


def test_final_runtime_rejects_console_entrypoint_bound_to_staging(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime" / ("a" * 64)
    python = runtime / "python/bin/python"
    entrypoint = runtime / "python/bin/ethos"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"python")
    entrypoint.write_text(
        f"#!{runtime.parent}/.runtime-staging/python/bin/python\n",
        encoding="utf-8",
    )
    entrypoint.chmod(0o755)
    install.write_runtime_manifest(
        runtime,
        "a" * 64,
        "b" * 64,
        _ENVIRONMENT,
        _BUILD_IDENTITY,
        python,
    )

    with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
        install.require_runtime(
            runtime,
            "a" * 64,
            "b" * 64,
            "cpython-test",
            _BUILD_IDENTITY,
        )


def test_finalize_runtime_rewrites_staging_entrypoint_before_smoke(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    digest = runtime_digest(
        wheel_sha256="b" * 64,
        build=_BUILD_IDENTITY,
        environment=_ENVIRONMENT,
    )
    runtime = tmp_path / digest
    python = runtime / "python/bin/python"
    entrypoint = runtime / "python/bin/ethos"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"python")
    entrypoint.write_text("#!/staging/python/bin/python\n", encoding="utf-8")
    entrypoint.chmod(0o755)
    install.write_runtime_manifest(
        runtime,
        runtime.name,
        "b" * 64,
        _ENVIRONMENT,
        _BUILD_IDENTITY,
        python,
    )
    observed: list[Path] = []
    monkeypatch.setattr(
        install,
        "python_facts",
        lambda _python: {
            "python_abi": _ENVIRONMENT.python_abi,
            "python_version": _ENVIRONMENT.python_version,
            "python_implementation": _ENVIRONMENT.python_implementation,
            "prefix": (runtime / "python").resolve().as_posix(),
            "base_prefix": (runtime / "python").resolve().as_posix(),
        },
    )
    monkeypatch.setattr(
        install.subprocess,
        "run",
        lambda command, **_kwargs: (
            observed.append(command[0]) or _completed(0, stdout="ethos-test\n")
        ),
    )

    install.finalize_runtime(
        runtime,
        runtime.name,
        "b" * 64,
        _BUILD_IDENTITY,
        _ENVIRONMENT,
    )

    assert entrypoint.read_text(encoding="utf-8").splitlines()[0] == f"#!{python}"
    assert observed == [entrypoint]
    payload = json.loads((runtime / "manifest.json").read_text(encoding="utf-8"))
    assert (
        payload["runtime_files"][entrypoint.relative_to(runtime).as_posix()]
        == hashlib.sha256(entrypoint.read_bytes()).hexdigest()
    )
