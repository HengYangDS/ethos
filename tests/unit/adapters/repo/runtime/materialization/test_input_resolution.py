"""Runtime materialization input-resolution contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.runtime.materialization.input_resolution as runtime_inputs
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_executable


def _completed(code: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess((), code, stdout, stderr)


def _node_supply(root: Path, node: Path) -> None:
    executable = root / node
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_bytes(b"node")
    executable.chmod(0o755)


@pytest.mark.parametrize(
    ("platform_name", "node_relative"),
    [("posix", Path("bin/node")), ("nt", Path("node.exe"))],
)
def test_node_runtime_resolves_the_installed_platform_layout(
    tmp_path: Path, platform_name: str, node_relative: Path
) -> None:
    _node_supply(tmp_path, node_relative)

    node = resolve_node_executable(
        package_root=tmp_path,
        platform_name=platform_name,
    )

    assert node == tmp_path / node_relative


def test_node_runtime_fails_before_build_for_an_incomplete_supply(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="package-local Node executable is unavailable"):
        resolve_node_executable(package_root=tmp_path, platform_name="nt")


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
            type("Selected", (), {"root": runtime, "wheel_sha256": wheel_sha256})()
            if candidate == runtime
            else None
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
    python.parent.mkdir(parents=True)
    python.write_text("python", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", python.as_posix())
    commands: list[tuple[str, ...]] = []

    def build(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if "build" in command:
            output = Path(command[-1])
            output.mkdir(parents=True, exist_ok=True)
            for index in range(wheel_count):
                (output / f"ethos-{index}.whl").write_bytes(b"wheel")
        return _completed(0)

    monkeypatch.setattr(runtime_inputs.subprocess, "run", build)
    with pytest.raises(ValueError, match="hook_runtime_wheel_invalid"):
        runtime_inputs.resolve_runtime_wheel(source, wheel_dir)
    assert commands[0] == (
        python.as_posix(),
        "-B",
        "-I",
        "-m",
        "uv",
        "build",
        "--offline",
        "--no-build-isolation",
        "--wheel",
        "--out-dir",
        commands[0][-1],
    )


def test_installed_wheel_resolution_rejects_missing_and_non_file_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert runtime_inputs.is_selected_runtime_source(tmp_path) is False
    for provenance in (
        None,
        json.dumps({"url": "https://example.test/ethos.whl"}),
        json.dumps({"url": "file://remote.test/D:/dist/ethos.whl"}),
    ):
        metadata = SimpleNamespace(read_text=lambda *_args, value=provenance: value)
        monkeypatch.setattr(runtime_inputs, "distribution", lambda _name, value=metadata: value)
        with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
            runtime_inputs.resolve_runtime_wheel(tmp_path, tmp_path / "wheel")


def test_installed_wheel_uses_native_file_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wheel = tmp_path / "ethos-0.2.0-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    metadata = SimpleNamespace(
        read_text=lambda *_args: json.dumps({"url": "file:///D:/dist/ethos.whl"})
    )
    monkeypatch.setattr(runtime_inputs, "distribution", lambda _name: metadata)

    def native_path(path: str) -> str:
        assert path == "/D:/dist/ethos.whl"
        return wheel.as_posix()

    monkeypatch.setattr(urllib.request, "url2pathname", native_path)

    assert (
        runtime_inputs.resolve_runtime_wheel(tmp_path / "installed", tmp_path / "unused") == wheel
    )


def test_managed_runtime_resolves_its_git_common_content_addressed_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, package_root = _managed_runtime_case(monkeypatch, tmp_path)
    wheel = package_root / "ethos-test.whl"
    wheel.parent.mkdir(parents=True)
    wheel.write_bytes(b"wheel")

    assert runtime_inputs.is_selected_runtime_source(source) is True
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


def test_runtime_tool_reports_module_stderr_without_writing_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    python = tmp_path / "bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("python", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", python.as_posix())
    monkeypatch.setattr(
        runtime_inputs.subprocess,
        "run",
        lambda *_args, **_kwargs: _completed(1, stderr="No module named uv"),
    )
    failed_wheel = tmp_path / "failed/wheel"
    with pytest.raises(ValueError, match="No module named uv"):
        runtime_inputs.resolve_runtime_wheel(source, failed_wheel)
    assert not failed_wheel.exists()

    def build(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "build" in command:
            output = Path(command[-1])
            output.mkdir(parents=True)
            (output / "ethos-retry.whl").write_bytes(b"wheel")
        return _completed(0)

    monkeypatch.setattr(runtime_inputs.subprocess, "run", build)
    assert runtime_inputs.resolve_runtime_wheel(source, failed_wheel).parent == failed_wheel


def test_runtime_tool_disables_persistent_cache_and_forces_copy_link_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    python = tmp_path / "bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("python", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", python.as_posix())
    supply = source / "node_modules"
    supply.mkdir()
    packages = {"node_modules/tool": {"version": "1.0.0"}}
    (source / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": {"": {}, **packages}}) + "\n",
        encoding="utf-8",
    )
    (supply / ".package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": packages}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)
    monkeypatch.setenv("UV_LINK_MODE", "hardlink")
    monkeypatch.setenv("UV_CACHE_DIR", (tmp_path / "ambient-cache").as_posix())
    monkeypatch.setenv("ETHOS_UV_CACHE_DIR", (tmp_path / "legacy-cache").as_posix())
    observed: dict[str, str] = {}

    def run(*_args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.update(kwargs["env"])
        return _completed(0)

    monkeypatch.setattr(runtime_inputs.subprocess, "run", run)

    runtime_inputs.run_runtime_tool(source, "pip", "install", "package.whl")

    assert observed["UV_LINK_MODE"] == "copy"
    assert observed["UV_NO_CACHE"] == "1"
    assert "UV_CACHE_DIR" not in observed
    assert "ETHOS_UV_CACHE_DIR" not in observed
    assert observed["ETHOS_NODE_PACKAGE_SUPPLY"] == supply.as_posix()


def test_runtime_tool_executes_uv_through_the_owned_python_module(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    python = tmp_path / "python/python.exe"
    python.parent.mkdir()
    python.write_text("python", encoding="utf-8")
    observed: list[tuple[str, ...]] = []
    monkeypatch.setattr(sys, "executable", python.as_posix())
    monkeypatch.setattr(
        runtime_inputs.subprocess,
        "run",
        lambda command, **_kwargs: observed.append(command) or _completed(0),
    )

    runtime_inputs.run_runtime_tool(source, "pip", "install", "package.whl")

    assert observed == [
        (
            python.as_posix(),
            "-B",
            "-I",
            "-m",
            "uv",
            "pip",
            "install",
            "package.whl",
        )
    ]


def test_runtime_project_selects_complete_source_or_complete_packaged_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for name in ("pyproject.toml", "uv.lock", "VERSION"):
        (source / name).write_text("x\n", encoding="utf-8")
    assert runtime_inputs.resolve_runtime_project(source) == source

    packaged = tmp_path / "package/ethos/data/runtime-project"
    packaged.mkdir(parents=True)
    for name in ("pyproject.toml", "uv.lock", "VERSION"):
        (packaged / name).write_text("x\n", encoding="utf-8")
    monkeypatch.setattr(
        runtime_inputs,
        "__file__",
        packaged.parents[1] / "a/b/c/d/input_resolution.py",
    )
    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    assert runtime_inputs.resolve_runtime_project(incomplete) == packaged

    (packaged / "VERSION").unlink()
    with pytest.raises(ValueError, match="hook_runtime_packaged_project_missing"):
        runtime_inputs.resolve_runtime_project(incomplete)
