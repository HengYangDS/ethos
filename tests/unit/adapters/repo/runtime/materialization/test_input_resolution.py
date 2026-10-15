"""Runtime materialization input-resolution contracts."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
import venv
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.runtime.materialization.input_resolution as runtime_inputs
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime


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
    npm = tmp_path / (
        "node_modules/npm/bin/npm-cli.js"
        if platform_name == "nt"
        else "lib/node_modules/npm/bin/npm-cli.js"
    )
    npm.parent.mkdir(parents=True)
    npm.write_text("// Native npm entrypoint.\n")

    node = resolve_node_runtime(
        package_root=tmp_path,
        platform_name=platform_name,
    )

    assert node.executable == tmp_path / node_relative
    assert node.npm == npm


def test_node_runtime_fails_before_build_for_an_incomplete_supply(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="package-local Node executable is unavailable"):
        resolve_node_runtime(package_root=tmp_path, platform_name="nt")


def test_node_runtime_rejects_an_executable_without_its_native_npm(tmp_path: Path) -> None:
    """A Node-only platform package cannot satisfy the complete runtime closure."""
    executable = tmp_path / "bin/node"
    executable.parent.mkdir()
    executable.touch(mode=0o755)

    with pytest.raises(ValueError, match="package-local npm CLI is unavailable"):
        resolve_node_runtime(package_root=tmp_path, platform_name="posix")


def test_runtime_inputs_cannot_escape_the_selected_root(tmp_path: Path) -> None:
    root = tmp_path / "native"
    node = root / "bin/node"
    node.parent.mkdir(parents=True)
    node.write_bytes(b"selected native bytes")
    node.chmod(0o755)
    npm = root / "lib/node_modules/npm/bin/npm-cli.js"
    npm.parent.mkdir(parents=True)
    outside = tmp_path / "foreign-npm.js"
    outside.write_text("// foreign executable\n")
    npm.symlink_to(outside)
    with pytest.raises(ValueError, match="native_node_runtime_path_invalid"):
        resolve_node_runtime(package_root=root, platform_name="posix")


def test_source_runtime_uses_the_locked_product_npm_not_the_bootstrap_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native Node archive does not own the product package-manager version."""
    native = tmp_path / "native"
    executable = native / "bin/node"
    executable.parent.mkdir(parents=True)
    executable.touch(mode=0o755)
    bootstrap = native / "lib/node_modules/npm/bin/npm-cli.js"
    bootstrap.parent.mkdir(parents=True)
    bootstrap.write_text("// Bootstrap-only npm.\n")
    product = tmp_path / "product/node_modules/npm"
    npm = product / "bin/npm-cli.js"
    npm.parent.mkdir(parents=True)
    npm.write_text("// Lock-owned product npm.\n")
    monkeypatch.setattr(runtime_inputs, "canonical_resource", lambda _: tmp_path / "pyproject.toml")
    monkeypatch.setattr(runtime_inputs, "packaged_resource", lambda *_: tmp_path / "installed")
    monkeypatch.setattr(
        runtime_inputs.NodeSupply,
        "read",
        lambda _: SimpleNamespace(installed_root=lambda _: native),
    )
    monkeypatch.setattr(runtime_inputs, "product_node_module", lambda _: product, raising=False)

    runtime = resolve_node_runtime()

    assert runtime.executable == executable
    assert runtime.npm == npm
    assert runtime.npm != bootstrap


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
    selected = runtime_inputs.selected_runtime_source(source)
    assert selected is not None
    assert selected.root == source.parents[3]
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


def test_invoking_runtime_names_its_exact_wheel_as_one_hashed_requirement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only a selected runtime holding its exact package wheel names a requirement."""
    assert runtime_inputs.invoking_runtime_requirement() is None
    source, package_root = _managed_runtime_case(monkeypatch, tmp_path)
    monkeypatch.setattr(runtime_inputs, "__file__", str(source / "ethos/input_resolution.py"))
    with pytest.raises(ValueError, match=r"^hook_runtime_wheel_provenance_missing$"):
        runtime_inputs.invoking_runtime_requirement()
    package_root.mkdir(parents=True)
    wheel = package_root / "ethos-0.2.0+local-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    digest = hashlib.sha256(b"wheel").hexdigest()
    requirement = runtime_inputs.invoking_runtime_requirement()
    assert requirement == f"ethos @ {wheel.as_uri()}#sha256={digest}"
    assert requirement.startswith("ethos @ file:///")
    assert "ethos-0.2.0%2Blocal-py3-none-any.whl#sha256=" in requirement

    def unreadable(_path: Path) -> str:
        raise PermissionError

    monkeypatch.setattr(runtime_inputs, "file_sha256", unreadable)
    with pytest.raises(ValueError, match=r"^hook_runtime_wheel_provenance_missing$"):
        runtime_inputs.invoking_runtime_requirement()


@pytest.mark.parametrize("layout", ["bin/python", "python/python.exe"])
@pytest.mark.parametrize(
    "operation", [("export",), ("sync",), ("pip", "install", "package.whl"), ("build",)]
)
def test_runtime_tool_preserves_interpreter_supply_and_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layout: str, operation: tuple[str, ...]
) -> None:
    """Keep native argv and all isolation obligations in one invocation fixture."""
    source, python = tmp_path / "source", tmp_path / layout
    source.mkdir()
    python.parent.mkdir(parents=True)
    python.write_text("python")
    monkeypatch.setattr(sys, "executable", str(python))
    supply = source / "node_modules"
    supply.mkdir()
    packages = {"node_modules/tool": {"version": "1.0.0"}}
    (source / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": {"": {}, **packages}})
    )
    building = operation == ("build",)
    if building:
        (supply / ".package-lock.json").write_text(
            json.dumps({"lockfileVersion": 3, "packages": packages})
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
    runtime_inputs.run_runtime_tool(source, *operation)
    assert len(observed) == 1
    command, env = observed[0]
    assert command == (str(python), "-B", "-I", "-m", "uv", *operation)
    assert {key: env[key] for key in ("UV_LINK_MODE", "UV_NO_CACHE", "UV_PYTHON")} == {
        "UV_LINK_MODE": "copy",
        "UV_NO_CACHE": "1",
        "UV_PYTHON": str(python),
    }
    assert not {"UV_CACHE_DIR", "ETHOS_UV_CACHE_DIR"} & env.keys()
    assert env.get("ETHOS_NODE_PACKAGE_SUPPLY") == (str(supply) if building else None)


def test_runtime_tool_targets_a_selected_environment_on_the_invoking_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two environments over one base interpreter remain distinct uv targets."""
    selected = tmp_path / "selected"
    venv.EnvBuilder(symlinks=os.name != "nt", with_pip=False).create(selected)
    python = selected / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    native = subprocess.run
    targets: list[str] = []

    def run(command, **kwargs):
        if tuple(command[1:5]) != ("-B", "-I", "-m", "uv"):
            return native(command, **kwargs)
        targets.append(kwargs["env"]["VIRTUAL_ENV"])
        return _completed(0)

    monkeypatch.setattr(runtime_inputs.subprocess, "run", run)
    runtime_inputs.run_runtime_tool(tmp_path, "sync", python=python)
    assert len(targets) == 1
    assert Path(targets[0]).samefile(selected)


def test_runtime_project_selects_complete_source_or_complete_packaged_resources(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for name in ("pyproject.toml", "uv.lock", "VERSION"):
        (source / name).write_text("x\n", encoding="utf-8")
    assert runtime_inputs.resolve_runtime_project(source) == source

    packaged = tmp_path / "package/ethos/resources"
    packaged.mkdir(parents=True)
    for name in ("pyproject.toml", "uv.lock", "VERSION"):
        (packaged / name).write_text("x\n", encoding="utf-8")
    monkeypatch.setattr(
        runtime_inputs,
        "packaged_resource",
        lambda: packaged,
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
