"""Runtime materialization input-resolution contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.runtime.materialization.input_resolution as runtime_inputs


def _completed(code: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess((), code, stdout, stderr)


def _managed_runtime_case(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    wheel_sha256 = hashlib.sha256(b"wheel").hexdigest()
    runtime = tmp_path / "repo.git/ethos/runtime" / ("a" * 64)
    source = runtime / "python/lib/python3.14/site-packages"
    source.mkdir(parents=True)
    monkeypatch.setattr(sys, "prefix", (runtime / "python").as_posix())
    monkeypatch.setattr(
        runtime_inputs,
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

    monkeypatch.setattr(runtime_inputs.subprocess, "run", build)
    with pytest.raises(ValueError, match="hook_runtime_wheel_invalid"):
        runtime_inputs.resolve_runtime_wheel(source, wheel_dir)
    assert commands[0][1:] == ("sync", "--locked", "--offline", "--check", "--active")
    assert "--no-build-isolation" in commands[1]


def test_installed_wheel_resolution_rejects_missing_and_non_file_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for provenance in (None, json.dumps({"url": "https://example.test/ethos.whl"})):
        metadata = type("Metadata", (), {"read_text": lambda *_args, value=provenance: value})()
        monkeypatch.setattr(runtime_inputs, "distribution", lambda _name, value=metadata: value)
        with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
            runtime_inputs.resolve_runtime_wheel(tmp_path, tmp_path / "wheel")


def test_managed_runtime_resolves_its_git_common_content_addressed_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, package_root = _managed_runtime_case(monkeypatch, tmp_path)
    wheel = package_root / "ethos-test.whl"
    wheel.parent.mkdir(parents=True)
    wheel.write_bytes(b"wheel")

    assert runtime_inputs.resolve_runtime_wheel(source, tmp_path / "unused") == wheel


def test_managed_runtime_rejects_missing_or_ambiguous_content_addressed_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, package_root = _managed_runtime_case(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
        runtime_inputs.resolve_runtime_wheel(source, tmp_path / "unused")

    package_root.mkdir(parents=True)
    (package_root / "ethos-drifted.whl").write_bytes(b"drifted")
    with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
        runtime_inputs.resolve_runtime_wheel(source, tmp_path / "unused")

    (package_root / "ethos-drifted.whl").unlink()
    for name in ("ethos-first.whl", "ethos-second.whl"):
        (package_root / name).write_bytes(b"wheel")
    with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
        runtime_inputs.resolve_runtime_wheel(source, tmp_path / "unused")


def test_runtime_tool_reports_missing_executable_and_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    missing_wheel_dir = tmp_path / "missing/wheel"
    monkeypatch.setattr(sys, "executable", (tmp_path / "bin/python").as_posix())
    with pytest.raises(ValueError, match="hook_runtime_uv_unavailable"):
        runtime_inputs.resolve_runtime_wheel(source, missing_wheel_dir)

    uv = tmp_path / "bin/uv"
    uv.parent.mkdir(parents=True)
    uv.write_text("tool", encoding="utf-8")
    monkeypatch.setattr(
        runtime_inputs.subprocess,
        "run",
        lambda *_args, **_kwargs: _completed(1, stderr="build failed"),
    )
    failed_wheel = tmp_path / "failed/wheel"
    with pytest.raises(ValueError, match="build failed"):
        runtime_inputs.resolve_runtime_wheel(source, failed_wheel)
    assert not failed_wheel.exists()

    def build(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[1] == "build":
            output = Path(command[-1])
            output.mkdir(parents=True)
            (output / "ethos-retry.whl").write_bytes(b"wheel")
        return _completed(0)

    monkeypatch.setattr(runtime_inputs.subprocess, "run", build)
    assert runtime_inputs.resolve_runtime_wheel(source, failed_wheel).parent == failed_wheel


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

    monkeypatch.setattr(runtime_inputs.subprocess, "run", reject)
    wheel_dir = tmp_path / "build/wheel"
    with pytest.raises(ValueError, match="source environment drift"):
        runtime_inputs.resolve_runtime_wheel(source, wheel_dir)

    assert commands == [(uv.as_posix(), "sync", "--locked", "--offline", "--check", "--active")]
    assert not wheel_dir.parent.exists()
