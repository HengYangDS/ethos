"""Immutable hook-runtime installation resolution boundaries."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.hook_runtime_install as install

if TYPE_CHECKING:
    from pathlib import Path


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

    def build(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        wheel_dir.mkdir(parents=True, exist_ok=True)
        for index in range(wheel_count):
            (wheel_dir / f"ethos-{index}.whl").write_bytes(b"wheel")
        return _completed(0)

    monkeypatch.setattr(install.subprocess, "run", build)
    with pytest.raises(ValueError, match="hook_runtime_wheel_invalid"):
        install.resolve_runtime_wheel(source, wheel_dir)


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


def test_installed_runtime_copy_rejects_python_outside_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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
        install.materialize_hook_runtime(tmp_path / "repo", tmp_path / "foreign/python")


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
    with pytest.raises(ValueError, match="build failed"):
        install.resolve_runtime_wheel(source, tmp_path / "failed" / "wheel")


def test_python_abi_and_manifest_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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
        install.materialize_hook_runtime(tmp_path / "repo", source_python)

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
        install.materialize_hook_runtime(tmp_path / "repo", source_python)


def test_materialize_installed_runtime_copies_exact_python_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "installed/lib/ethos/adapters/repo/hook_runtime_install.py"
    source.parent.mkdir(parents=True)
    source.write_text("installed", encoding="utf-8")
    prefix = tmp_path / "prefix"
    python = prefix / "bin/python"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"python")
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

    runtime = install.materialize_hook_runtime(tmp_path / "repo", python)

    assert (runtime / "bin/python").read_bytes() == b"python"
