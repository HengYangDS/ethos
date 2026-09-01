"""Runtime materialization input-resolution contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.runtime.materialization.input_resolution as runtime_inputs
import ethos.adapters.repo.runtime.materialization.python_image as python_image
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_executable
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_openspec_supply


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


def test_openspec_supply_prefers_an_explicit_prepared_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    supply = tmp_path / "prepared/node_modules"
    source.mkdir()
    supply.mkdir(parents=True)
    monkeypatch.setenv("ETHOS_BUILD_OPENSPEC_SUPPLY", supply.as_posix())

    assert resolve_openspec_supply(source) == supply.resolve()


def test_openspec_supply_rejects_an_unprepared_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ETHOS_BUILD_OPENSPEC_SUPPLY", raising=False)
    with pytest.raises(ValueError, match="openspec_build_supply_unavailable"):
        resolve_openspec_supply(tmp_path)


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
    assert commands[0][1:] == (
        "sync",
        "--locked",
        "--offline",
        "--check",
        "--active",
        "--no-install-project",
        "--inexact",
    )
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


def test_runtime_tool_forces_copy_link_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    python = tmp_path / "bin/python"
    uv = python.with_name("uv")
    uv.parent.mkdir(parents=True)
    uv.write_text("tool", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", python.as_posix())
    supply = source / "node_modules"
    supply.mkdir()
    (source / "package-lock.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.delenv("ETHOS_BUILD_OPENSPEC_SUPPLY", raising=False)
    monkeypatch.setenv("UV_LINK_MODE", "hardlink")
    monkeypatch.setenv("UV_CACHE_DIR", (tmp_path / "ambient-cache").as_posix())
    observed: dict[str, str] = {}

    def run(*_args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.update(kwargs["env"])
        return _completed(0)

    monkeypatch.setattr(runtime_inputs.subprocess, "run", run)

    runtime_inputs.run_runtime_tool(source, "pip", "install", "package.whl")

    assert observed["UV_LINK_MODE"] == "copy"
    assert observed["UV_CACHE_DIR"] == (tmp_path / "ambient-cache").as_posix()
    assert observed["ETHOS_BUILD_OPENSPEC_SUPPLY"] == supply.as_posix()


def test_locked_closure_prefills_owned_cache_then_installs_offline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source, work, interpreter = tmp_path / "source", tmp_path / "work", tmp_path / "python"
    wheel, cache = tmp_path / "ethos.whl", tmp_path / "cache"
    source.mkdir()
    interpreter.write_text("python", encoding="utf-8")
    wheel.write_bytes(b"wheel")
    commands: list[tuple[str, ...]] = []
    cache_ready = False

    def run(
        _source: Path,
        *command: str,
        cache_dir: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal cache_ready
        assert cache_dir == cache
        commands.append(command)
        if command[0] == "export":
            output = Path(command[command.index("--output-file") + 1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("package==1 --hash=sha256:abc\n", encoding="utf-8")
        elif command[:2] == ("pip", "sync") and "--offline" not in command:
            target = Path(command[command.index("--target") + 1])
            target.mkdir(parents=True)
            (target / "package.py").write_text("cached\n", encoding="utf-8")
            cache_ready = True
        elif "--offline" in command:
            assert cache_ready
        return _completed(0)

    monkeypatch.setattr(python_image, "run_runtime_tool", run)

    requirements = python_image.prepare_locked_requirements(
        source,
        work,
        interpreter,
        cache_dir=cache,
    )
    python_image.install_locked_runtime(
        source,
        interpreter,
        wheel,
        requirements,
        cache_dir=cache,
    )

    assert [command[:2] for command in commands] == [
        ("export", "--locked"),
        ("pip", "sync"),
        ("pip", "sync"),
        ("pip", "install"),
    ]
    assert "--offline" not in commands[1]
    assert "--target" in commands[1]
    assert "--require-hashes" in commands[1]
    assert "--offline" in commands[2]
    assert "--offline" in commands[3]
    assert not (work / "dependency-preflight").exists()


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

    assert commands == [
        (
            uv.as_posix(),
            "sync",
            "--locked",
            "--offline",
            "--check",
            "--active",
            "--no-install-project",
            "--inexact",
        )
    ]
    assert not wheel_dir.parent.exists()


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


def test_owned_interpreter_reuses_runtime_or_installs_one_managed_python(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime = tmp_path / "repo.git/ethos/runtime" / ("a" * 64)
    prefix = runtime / "python"
    interpreter = prefix / "bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("python", encoding="utf-8")
    monkeypatch.setattr(sys, "prefix", prefix.as_posix())
    assert runtime_inputs.resolve_owned_interpreter(tmp_path, interpreter) == interpreter.resolve()

    source_python = tmp_path / "source-python"
    source_python.write_text("python", encoding="utf-8")
    managed = tmp_path / "managed/python"
    managed.parent.mkdir(parents=True)
    managed.write_text("python", encoding="utf-8")
    uv = prefix / "bin/uv"
    uv.write_text("uv", encoding="utf-8")
    monkeypatch.setattr(sys, "prefix", (tmp_path / "ambient").as_posix())
    monkeypatch.setattr(sys, "executable", (prefix / "bin/python").as_posix())
    monkeypatch.setattr(
        runtime_inputs,
        "observe_python_facts",
        lambda path: (
            {"python_version": "3.14", "prefix": "source", "base_prefix": "source"}
            if path == source_python
            else {"prefix": "managed", "base_prefix": "managed"}
        ),
    )
    calls = 0

    def run(_command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        return _completed(1) if calls == 1 else _completed(0, managed.as_posix())

    monkeypatch.setattr(runtime_inputs.subprocess, "run", run)

    assert runtime_inputs.resolve_owned_interpreter(tmp_path, source_python) == managed.resolve()
    assert calls == 3


def test_owned_interpreter_reports_install_and_validation_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source_python = tmp_path / "source-python"
    source_python.write_text("python", encoding="utf-8")
    python = tmp_path / "bin/python"
    uv = python.with_name("uv")
    uv.parent.mkdir(parents=True)
    uv.write_text("uv", encoding="utf-8")
    monkeypatch.setattr(sys, "executable", python.as_posix())
    monkeypatch.setattr(
        runtime_inputs,
        "observe_python_facts",
        lambda path: (
            {"python_version": "3.14", "prefix": "source", "base_prefix": "source"}
            if path == source_python
            else {"prefix": "venv", "base_prefix": "base"}
        ),
    )
    monkeypatch.setattr(
        runtime_inputs.subprocess,
        "run",
        lambda command, **_kwargs: (
            _completed(1, stderr="install failed") if "install" in command else _completed(1)
        ),
    )
    with pytest.raises(ValueError, match="install failed"):
        runtime_inputs.resolve_owned_interpreter(tmp_path, source_python)

    candidate = tmp_path / "managed/python"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("python", encoding="utf-8")
    monkeypatch.setattr(
        runtime_inputs.subprocess,
        "run",
        lambda *_args, **_kwargs: _completed(0, candidate.as_posix()),
    )
    with pytest.raises(ValueError, match="hook_runtime_owned_interpreter_unavailable"):
        runtime_inputs.resolve_owned_interpreter(tmp_path, source_python)
