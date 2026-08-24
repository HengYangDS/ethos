"""Immutable hook-runtime installation resolution boundaries."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.hook_runtime_install as install

_SOURCE_IDENTITY = install.RuntimeSourceIdentity(commit="a" * 40, tree="b" * 40)


def _bind_source_identity(monkeypatch: pytest.MonkeyPatch) -> install.RuntimeSourceIdentity:
    monkeypatch.setattr(install, "wheel_source_identity", lambda _wheel: _SOURCE_IDENTITY)
    return _SOURCE_IDENTITY


def _completed(code: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess((), code, stdout, stderr)


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
    digest = "a" * 64
    wheel_sha256 = hashlib.sha256(b"wheel").hexdigest()
    runtime = tmp_path / "repo.git/ethos/runtime" / digest
    source = runtime / "venv/lib/python3.14/site-packages"
    source.mkdir(parents=True)
    wheel = tmp_path / "repo.git/ethos/packages" / wheel_sha256 / "ethos-test.whl"
    wheel.parent.mkdir(parents=True)
    wheel.write_bytes(b"wheel")
    monkeypatch.setattr(sys, "prefix", (runtime / "venv").as_posix())
    monkeypatch.setattr(
        install,
        "require_selected_runtime",
        lambda candidate: (
            type("Selected", (), {"wheel_sha256": wheel_sha256})() if candidate == runtime else None
        ),
    )

    assert install.resolve_runtime_wheel(source, tmp_path / "unused") == wheel


def test_managed_runtime_rejects_missing_or_ambiguous_content_addressed_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    digest = "a" * 64
    wheel_sha256 = hashlib.sha256(b"wheel").hexdigest()
    runtime = tmp_path / "repo.git/ethos/runtime" / digest
    source = runtime / "venv/lib/python3.14/site-packages"
    source.mkdir(parents=True)
    package_root = tmp_path / "repo.git/ethos/packages" / wheel_sha256
    monkeypatch.setattr(sys, "prefix", (runtime / "venv").as_posix())
    monkeypatch.setattr(
        install,
        "require_selected_runtime",
        lambda candidate: (
            type("Selected", (), {"wheel_sha256": wheel_sha256})() if candidate == runtime else None
        ),
    )

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


def test_installed_runtime_copy_rejects_python_outside_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _bind_source_identity(monkeypatch)
    source = tmp_path / "installed/a/b/c/d"
    source.mkdir(parents=True)
    wheel = tmp_path / "ethos.whl"
    wheel.write_bytes(b"wheel")
    common = tmp_path / "repo.git"
    common.mkdir()
    monkeypatch.setattr(install, "__file__", (source / "module.py").as_posix())
    monkeypatch.setattr(install, "git_common_dir", lambda _repo: common.as_posix())
    monkeypatch.setattr(install, "resolve_runtime_wheel", lambda *_args: wheel)
    monkeypatch.setattr(sys, "prefix", (tmp_path / "prefix").as_posix())
    monkeypatch.setattr(
        install.subprocess,
        "run",
        lambda *_args, **_kwargs: _completed(0, stdout="cpython-test\n"),
    )

    with pytest.raises(ValueError, match="hook_runtime_python_prefix_invalid"):
        install.materialize_hook_runtime(
            tmp_path / "repo",
            tmp_path / "foreign/python",
            expected_source=_SOURCE_IDENTITY,
        )


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
    _bind_source_identity(monkeypatch)
    source = tmp_path / "installed/a/b/c/d"
    source.mkdir(parents=True)
    wheel = tmp_path / "ethos.whl"
    wheel.write_bytes(b"wheel")
    common = tmp_path / "repo.git"
    common.mkdir()
    prefix = tmp_path / "prefix"
    source_python = prefix / "bin/python"
    source_python.parent.mkdir(parents=True)
    source_python.write_bytes(b"python")
    monkeypatch.setattr(install, "__file__", (source / "module.py").as_posix())
    monkeypatch.setattr(install, "git_common_dir", lambda _repo: common.as_posix())
    monkeypatch.setattr(install, "resolve_runtime_wheel", lambda *_args: wheel)
    monkeypatch.setattr(sys, "prefix", prefix.as_posix())
    monkeypatch.setattr(install.subprocess, "run", lambda *_args, **_kwargs: _completed(1))
    with pytest.raises(ValueError, match="hook_runtime_python_abi_invalid"):
        install.materialize_hook_runtime(
            tmp_path / "repo", source_python, expected_source=_SOURCE_IDENTITY
        )

    monkeypatch.setattr(
        install.subprocess,
        "run",
        lambda *_args, **_kwargs: _completed(0, stdout="cpython-test\n"),
    )
    monkeypatch.setattr(
        install.shutil,
        "copytree",
        lambda _source, target, **_kwargs: target.mkdir(parents=True),
    )
    with pytest.raises(ValueError, match="hook_runtime_python_missing"):
        install.materialize_hook_runtime(
            tmp_path / "repo", source_python, expected_source=_SOURCE_IDENTITY
        )


def test_materialize_installed_runtime_copies_exact_python_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _bind_source_identity(monkeypatch)
    source = tmp_path / "installed/lib/ethos/adapters/repo/hook_runtime_install.py"
    source.parent.mkdir(parents=True)
    source.write_text("installed", encoding="utf-8")
    prefix = tmp_path / "prefix"
    host_python = tmp_path / "host/python"
    host_python.parent.mkdir(parents=True)
    host_python.write_bytes(b"python")
    python = prefix / "bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(host_python)
    entrypoint = prefix / "bin/ethos"
    entrypoint.write_text(f"#!{python}\n", encoding="utf-8")
    entrypoint.chmod(0o755)
    common = tmp_path / "repo.git"
    common.mkdir()
    wheel = tmp_path / "ethos.whl"
    wheel.write_bytes(b"wheel")
    monkeypatch.setattr(install, "__file__", source.as_posix())
    monkeypatch.setattr(sys, "prefix", prefix.as_posix())
    monkeypatch.setattr(install, "git_common_dir", lambda _repo: common.as_posix())
    monkeypatch.setattr(
        install.subprocess,
        "run",
        lambda *_args, **_kwargs: _completed(0, stdout="cpython-test\n"),
    )
    monkeypatch.setattr(install, "resolve_runtime_wheel", lambda *_args: wheel)

    runtime = install.materialize_hook_runtime(
        tmp_path / "repo", python, expected_source=_SOURCE_IDENTITY
    )

    assert (runtime / "bin/python").read_bytes() == b"python"
    assert not (runtime / "bin/python").is_symlink()


def test_materialize_runtime_installs_from_durable_content_addressed_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _bind_source_identity(monkeypatch)
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
    source_python = tmp_path / "bin/python"
    source_python.parent.mkdir()
    source_python.write_bytes(b"python")
    monkeypatch.setattr(sys, "prefix", tmp_path.as_posix())
    calls: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(install, "__file__", module.as_posix())
    monkeypatch.setattr(install, "git_common_dir", lambda _repo: common.as_posix())
    monkeypatch.setattr(install, "resolve_runtime_wheel", lambda *_args: volatile_wheel)
    monkeypatch.setattr(install, "_python_abi", lambda _python: "cpython-test")

    def copy_runtime(_source: Path, target: Path, **_kwargs: object) -> None:
        python = target / "bin/python"
        python.parent.mkdir(parents=True)
        python.write_bytes(b"python")
        entrypoint = target / "bin/ethos"
        entrypoint.write_text(f"#!{python}\n", encoding="utf-8")
        entrypoint.chmod(0o755)

    monkeypatch.setattr(install.shutil, "copytree", copy_runtime)

    def run_runtime_tool(_source: Path, operation: str, *args: str) -> None:
        calls.append((operation, args))

    monkeypatch.setattr(install, "_run_runtime_tool", run_runtime_tool)
    monkeypatch.setattr(
        install.subprocess,
        "run",
        lambda *_args, **_kwargs: _completed(0, stdout="ethos-test\n"),
    )

    install.materialize_hook_runtime(
        tmp_path / "repo", source_python, expected_source=_SOURCE_IDENTITY
    )
    volatile_wheel.unlink()

    durable = common / "ethos/packages" / wheel_sha256 / volatile_wheel.name
    assert calls[0][1][:4] == ("--locked", "--offline", "--no-dev", "--no-emit-project")
    assert calls[1][0] == "pip"
    assert calls[1][1][:3] == ("sync", "--offline", "--require-hashes")
    assert "--strict" in calls[1][1]
    assert calls[2][0] == "pip"
    assert {"install", "--offline", "--no-deps"} < set(calls[2][1])
    assert Path(calls[2][1][-1]) == durable
    assert durable.read_bytes() == b"wheel"


def test_materialize_runtime_rejects_durable_wheel_digest_collision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _bind_source_identity(monkeypatch)
    source = tmp_path / "installed/a/b/c/d"
    source.mkdir(parents=True)
    wheel = tmp_path / "ethos-test.whl"
    wheel.write_bytes(b"wheel")
    wheel_sha256 = hashlib.sha256(b"wheel").hexdigest()
    common = tmp_path / "repo.git"
    durable = common / "ethos/packages" / wheel_sha256 / wheel.name
    durable.parent.mkdir(parents=True)
    durable.write_bytes(b"different")
    prefix = tmp_path / "prefix"
    source_python = prefix / "bin/python"
    source_python.parent.mkdir(parents=True)
    source_python.write_bytes(b"python")
    monkeypatch.setattr(install, "__file__", (source / "module.py").as_posix())
    monkeypatch.setattr(install, "git_common_dir", lambda _repo: common.as_posix())
    monkeypatch.setattr(install, "resolve_runtime_wheel", lambda *_args: wheel)
    monkeypatch.setattr(install, "_python_abi", lambda _python: "cpython-test")
    monkeypatch.setattr(sys, "prefix", prefix.as_posix())

    with pytest.raises(ValueError, match="hook_runtime_wheel_digest_collision"):
        install.materialize_hook_runtime(
            tmp_path / "repo", source_python, expected_source=_SOURCE_IDENTITY
        )


def test_final_runtime_rejects_console_entrypoint_bound_to_staging(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime" / ("a" * 64)
    python = runtime / "venv/bin/python"
    entrypoint = runtime / "venv/bin/ethos"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"python")
    entrypoint.write_text(
        f"#!{runtime.parent}/.runtime-staging/venv/bin/python\n",
        encoding="utf-8",
    )
    entrypoint.chmod(0o755)
    install.write_runtime_manifest(
        runtime,
        "a" * 64,
        "b" * 64,
        "cpython-test",
        _SOURCE_IDENTITY,
        python,
    )

    with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
        install.require_runtime(
            runtime,
            "a" * 64,
            "b" * 64,
            "cpython-test",
            _SOURCE_IDENTITY,
        )


def test_finalize_runtime_rewrites_staging_entrypoint_before_smoke(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = tmp_path / ("a" * 64)
    python = runtime / "venv/bin/python"
    entrypoint = runtime / "venv/bin/ethos"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"python")
    entrypoint.write_text("#!/staging/venv/bin/python\n", encoding="utf-8")
    entrypoint.chmod(0o755)
    install.write_runtime_manifest(
        runtime,
        runtime.name,
        "b" * 64,
        "cpython-test",
        _SOURCE_IDENTITY,
        python,
    )
    observed: list[Path] = []
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
        "cpython-test",
        _SOURCE_IDENTITY,
    )

    assert entrypoint.read_text(encoding="utf-8").splitlines()[0] == f"#!{python}"
    assert observed == [entrypoint]
    payload = json.loads((runtime / "manifest.json").read_text(encoding="utf-8"))
    assert (
        payload["runtime_files"][entrypoint.relative_to(runtime).as_posix()]
        == hashlib.sha256(entrypoint.read_bytes()).hexdigest()
    )
