"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.runtime.materialization.effect as runtime_materialization
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import runtime_executable


def test_runtime_inventory_hashes_actual_bytes_without_location_aliases(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for runtime in (first, second):
        script = runtime / "python/bin/ethos"
        script.parent.mkdir(parents=True)
        script.write_text(f"#!{runtime}/python/bin/python\n", encoding="utf-8")

    assert runtime_file_inventory(first) != runtime_file_inventory(second)


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
        manifest.write_text("not-json", encoding="utf-8")
    elif drift == "schema":
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["schema_version"] = 1
        manifest.write_text(json.dumps(payload), encoding="utf-8")
    elif drift == "python":
        python.unlink()
    elif drift == "hash":
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
            "source_commit": "source_commit",
            "source_tree": "source_tree",
            "files": "runtime_files",
        }[drift]
        payload[key] = {} if drift == "files" else "drift"
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
