"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_environment
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import runtime_build
from tests.support.runtime_scenarios import runtime_executable


def test_runtime_inventory_hashes_actual_bytes_without_location_aliases(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for runtime in (first, second):
        script = runtime / "python/bin/ethos"
        script.parent.mkdir(parents=True)
        script.write_text(f"#!{runtime}/python/bin/python\n", encoding="utf-8")

    assert runtime_file_inventory(first) != runtime_file_inventory(second)


def test_runtime_identity_distinguishes_canonical_architectures() -> None:
    common = {
        "python_abi": "cpython-314",
        "python_version": "3.14.7",
        "python_implementation": "cpython",
        "dependency_lock_sha256": "d" * 64,
        "platform_name": "linux",
    }
    arm = runtime_environment(**common, architecture_name="aarch64")
    x86 = runtime_environment(**common, architecture_name="AMD64")
    inputs = {
        "wheel_sha256": "e" * 64,
        "build": runtime_build("a" * 40, "b" * 40),
        "runtime_files": {"python": "f" * 64},
    }

    assert arm.architecture == "arm64"
    assert x86.architecture == "x86_64"
    assert runtime_digest(**inputs, environment=arm) != runtime_digest(**inputs, environment=x86)


@pytest.mark.parametrize(
    "drift",
    [
        "manifest",
        "schema",
        "digest",
        "wheel",
        "abi",
        "python_version",
        "dependency_lock",
        "platform",
        "architecture",
        "source_commit",
        "source_tree",
        "files",
        "python",
        "hash",
    ],
)
def test_hook_runtime_manifest_rejects_every_binding_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    runtime = venv.parent
    manifest = runtime / "manifest.json"
    python = runtime_executable(venv, "python")
    if drift == "manifest":
        manifest.chmod(0o644)
        manifest.write_text("not-json", encoding="utf-8")
    elif drift == "schema":
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["schema_version"] = 1
        manifest.chmod(0o644)
        manifest.write_text(json.dumps(payload), encoding="utf-8")
    elif drift == "python":
        python.parent.chmod(0o755)
        python.unlink()
    elif drift == "hash":
        python.chmod(0o755)
        python.write_text("drift\n", encoding="utf-8")
    else:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        key = {
            "digest": "runtime_digest",
            "wheel": "wheel_sha256",
            "abi": "python_abi",
            "python_version": "python_version",
            "dependency_lock": "dependency_lock_sha256",
            "platform": "platform",
            "architecture": "architecture",
            "source_commit": "source_commit",
            "source_tree": "source_tree",
            "files": "runtime_files",
        }[drift]
        payload[key] = {} if drift == "files" else "drift"
        manifest.chmod(0o644)
        manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
        runtime_materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=expected_runtime_build(repo)[0],
        )


@pytest.mark.parametrize("kind", ["absolute", "outside", "dangling", "cyclic"])
def test_runtime_inventory_rejects_non_closed_symlinks(tmp_path: Path, kind: str) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = runtime / "target"
    target.write_text("owned\n", encoding="utf-8")
    link = runtime / "link"
    if kind == "absolute":
        link.symlink_to(target)
    elif kind == "outside":
        external = tmp_path / "external"
        external.write_text("external\n", encoding="utf-8")
        link.symlink_to(Path("../external"))
    elif kind == "dangling":
        link.symlink_to(Path("missing"))
    else:
        link.symlink_to(Path("cycle"))
        (runtime / "cycle").symlink_to(Path("link"))

    with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
        runtime_file_inventory(runtime)


def test_runtime_inventory_rejects_a_junction_without_reading_its_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "runtime"
    junction = runtime / "junction"
    junction.mkdir(parents=True)
    sentinel = junction / "sentinel"
    sentinel.write_text("outside authority\n", encoding="utf-8")
    monkeypatch.setattr(
        runtime_filesystem,
        "is_junction",
        lambda path: path == junction,
    )

    with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
        runtime_file_inventory(runtime)

    assert sentinel.read_text(encoding="utf-8") == "outside authority\n"


def test_runtime_inventory_rejects_bytecode_and_cache_residue(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    cache = runtime / "python/lib/python3.14/site-packages/ethos/__pycache__"
    cache.mkdir(parents=True)
    (cache / "module.cpython-314.pyc").write_bytes(b"bytecode")

    with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
        runtime_file_inventory(runtime)


def test_runtime_inventory_hashes_an_internal_relative_symlink(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "target").write_text("owned\n", encoding="utf-8")
    (runtime / "link").symlink_to(Path("target"))

    inventory = runtime_file_inventory(runtime)

    assert inventory.keys() == {"link", "target"}
