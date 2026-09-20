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


@pytest.mark.parametrize(
    ("platform_name", "node_relative"),
    [("posix", Path("bin/node")), ("nt", Path("node.exe"))],
)
def test_node_runtime_resolves_the_installed_platform_layout(
    tmp_path: Path, platform_name: str, node_relative: Path
) -> None:
    executable = tmp_path / node_relative
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.touch(mode=0o755)

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
            SimpleNamespace(root=runtime, wheel_sha256=wheel_sha256)
            if candidate == runtime
            else None
        ),
    )
    return source, tmp_path / "repo.git/ethos/packages" / wheel_sha256


@pytest.mark.parametrize("outcome", [0, 2, "failure"])
def test_source_wheel_resolution_preserves_output_and_failure_contract(
    tmp_path, monkeypatch, outcome
):
    """Reject ambiguous output and preserve tool failures, with a recoverable retry."""
    source, python, destination = tmp_path / "source", tmp_path / "bin/python", tmp_path / "wheel"
    source.mkdir()
    (source / "pyproject.toml").write_text("[build-system]\n")
    python.parent.mkdir()
    python.touch()
    monkeypatch.setattr(sys, "executable", str(python))
    calls = []

    def build(command, **_kwargs):
        calls.append(command)
        if outcome == "failure":
            return _completed(1, stderr="No module named uv")
        output = Path(command[-1])
        output.mkdir(parents=True)
        for index in range(outcome):
            (output / f"ethos-{index}.whl").write_bytes(b"wheel")
        return _completed(0)

    monkeypatch.setattr(runtime_inputs.subprocess, "run", build)
    error = "No module named uv" if outcome == "failure" else "hook_runtime_wheel_invalid"
    with pytest.raises(ValueError, match=error):
        runtime_inputs.resolve_runtime_wheel(source, destination)
    assert not destination.exists()
    assert calls[0] == (
        str(python),
        "-B",
        "-I",
        "-m",
        "uv",
        "build",
        "--offline",
        "--no-build-isolation",
        "--wheel",
        "--out-dir",
        calls[0][-1],
    )
    outcome = 1
    assert runtime_inputs.resolve_runtime_wheel(source, destination).parent == destination


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


@pytest.mark.parametrize("contents", [[], [b"wheel"], [b"drifted"], [b"wheel", b"wheel"]])
def test_managed_runtime_requires_one_exact_wheel(tmp_path, monkeypatch, contents):
    """Resolve the package by verified content identity, not directory presence."""
    source, package_root = _managed_runtime_case(monkeypatch, tmp_path)
    assert runtime_inputs.is_selected_runtime_source(source) is True
    if contents:
        package_root.mkdir(parents=True)
        for index, content in enumerate(contents):
            (package_root / f"ethos-{index}.whl").write_bytes(content)
    if contents == [b"wheel"]:
        assert runtime_inputs.resolve_runtime_wheel(source, tmp_path / "unused") == (
            package_root / "ethos-0.whl"
        )
    else:
        with pytest.raises(ValueError, match="hook_runtime_wheel_provenance_missing"):
            runtime_inputs.resolve_runtime_wheel(source, tmp_path / "unused")


@pytest.mark.parametrize("layout", ["bin/python", "python/python.exe"])
def test_runtime_tool_preserves_interpreter_supply_and_environment(tmp_path, monkeypatch, layout):
    """Keep native argv and all isolation obligations in one invocation fixture."""
    source, python = tmp_path / "source", tmp_path / layout
    source.mkdir()
    python.parent.mkdir(parents=True)
    python.write_text("python")
    monkeypatch.setattr(sys, "executable", str(python))
    supply = source / "node_modules"
    supply.mkdir()
    packages = {"node_modules/tool": {"version": "1.0.0"}}
    for path, entries in ((source, {"": {}, **packages}), (supply, packages)):
        (path / (".package-lock.json" if path == supply else "package-lock.json")).write_text(
            json.dumps({"lockfileVersion": 3, "packages": entries})
        )
    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)
    for key, value in {
        "UV_LINK_MODE": "hardlink",
        "UV_PYTHON": "/unrelated/interpreter",
        "UV_CACHE_DIR": str(tmp_path / "ambient-cache"),
        "ETHOS_UV_CACHE_DIR": str(tmp_path / "legacy-cache"),
    }.items():
        monkeypatch.setenv(key, value)
    observed = []

    def run(command, **kwargs):
        observed.append((command, kwargs["env"]))
        return _completed(0)

    monkeypatch.setattr(runtime_inputs.subprocess, "run", run)
    runtime_inputs.run_runtime_tool(source, "pip", "install", "package.whl")
    assert len(observed) == 1
    command, env = observed[0]
    assert command == (str(python), "-B", "-I", "-m", "uv", "pip", "install", "package.whl")
    assert {key: env[key] for key in ("UV_LINK_MODE", "UV_NO_CACHE", "UV_PYTHON")} == {
        "UV_LINK_MODE": "copy",
        "UV_NO_CACHE": "1",
        "UV_PYTHON": str(python),
    }
    assert not {"UV_CACHE_DIR", "ETHOS_UV_CACHE_DIR"} & env.keys()
    assert env["ETHOS_NODE_PACKAGE_SUPPLY"] == str(supply)


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


@pytest.mark.parametrize("prefix_owner", ["project", "foreign"])
def test_locked_environment_python_requires_the_project_venv_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, prefix_owner: str
) -> None:
    project = tmp_path / "project"
    environment = project / ".venv"
    python = environment / (
        "Scripts/python.exe" if runtime_inputs.os.name == "nt" else "bin/python"
    )
    python.parent.mkdir(parents=True)
    python.write_bytes(b"python")
    prefix = environment if prefix_owner == "project" else tmp_path / "foreign"
    monkeypatch.setattr(
        runtime_inputs,
        "observe_python_facts",
        lambda _python: {
            "executable": python.as_posix(),
            "prefix": prefix.as_posix(),
        },
    )

    if prefix_owner == "foreign":
        with pytest.raises(ValueError, match="hook_runtime_locked_environment_invalid"):
            runtime_inputs.resolve_locked_environment_python(project)
    else:
        assert runtime_inputs.resolve_locked_environment_python(project) == python
