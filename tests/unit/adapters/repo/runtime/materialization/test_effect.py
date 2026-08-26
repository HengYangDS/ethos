"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.hook.activation as hook_activation
import ethos.adapters.repo.runtime.materialization.python_image as runtime_python_image
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.activation import install_hook_launchers
from tests.support.runtime_scenarios import git_process


def test_materialized_python_is_a_product_owned_non_mutating_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "managed-python"
    interpreter = home / "bin/python3.14"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_bytes(b"python-runtime")
    interpreter.chmod(0o755)
    stdlib = home / "lib/python3.14"
    stdlib.mkdir(parents=True)
    (stdlib / "os.py").write_text("# stdlib\n", encoding="utf-8")
    (stdlib / "test").mkdir()
    (stdlib / "test/support.py").write_text("# test-only\n", encoding="utf-8")
    (home / "include").mkdir()
    (home / "include/Python.h").write_text("/* build-only */\n", encoding="utf-8")
    (home / "share").mkdir()
    (home / "share/python.1").write_text("manual\n", encoding="utf-8")
    target = tmp_path / "runtime/python"

    monkeypatch.setattr(
        runtime_python_image,
        "observe_python_facts",
        lambda _python: {
            "python_abi": "cpython-test",
            "python_version": "3.14.7",
            "python_implementation": "cpython",
            "prefix": home.as_posix(),
            "base_prefix": home.as_posix(),
        },
    )

    def install(
        _source: Path,
        _work: Path,
        python: Path,
        _wheel: Path,
    ) -> None:
        scripts = python.parent
        for name in ("ethos", "uv"):
            script = scripts / name
            script.write_text(
                f"#!{target}/staging-python\nprint({name!r})\n",
                encoding="utf-8",
            )
            script.chmod(0o755)
        cache = target / "lib/python3.14/site-packages/ethos/__pycache__"
        cache.mkdir(parents=True)
        (cache / "module.cpython-314.pyc").write_bytes(b"bytecode")

    monkeypatch.setattr(runtime_python_image, "install_locked_runtime", install)
    monkeypatch.setattr(
        runtime_python_image,
        "console_script_entries",
        lambda _python: {"ethos": "ethos.cli:main", "uv": "uv:main"},
        raising=False,
    )

    materialize_python = runtime_python_image.materialize_python_image
    materialize_python(
        target,
        tmp_path,
        interpreter,
        tmp_path / "ethos.whl",
        tmp_path / "work",
        locked=True,
    )

    assert (target / "bin/python").read_bytes() == b"python-runtime"
    assert not (target / "include").exists()
    assert not (target / "share").exists()
    assert not (target / "lib/python3.14/test").exists()
    assert not tuple(target.rglob("__pycache__"))
    assert not tuple(target.rglob("*.pyc"))
    for name in ("ethos", "uv"):
        script = target / "bin" / name
        text = script.read_text(encoding="utf-8")
        assert text.startswith("#!/bin/sh\n")
        assert " -B -I " in text
        assert target.as_posix() not in text


def test_hook_install_materializes_a_common_dir_package_runtime(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    checkout_python = tmp_path / "stale-checkout" / ".venv" / "bin" / "python"
    checkout_python.parent.mkdir(parents=True)
    checkout_python.symlink_to(Path(sys.executable))

    report = install_hook_launchers(repo, python=checkout_python)
    common_runtime = Path(git_common_dir(repo)) / "ethos" / "runtime"

    assert Path(str(report["python"])).is_relative_to(common_runtime)
    manifest = Path(str(report["runtime_manifest_path"]))
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["runtime_digest"] == report["runtime_digest"]
    assert payload["wheel_sha256"] == report["wheel_sha256"]
    assert len(payload["wheel_sha256"]) == 64
    assert report["scripts"] == ["pre-commit", "pre-push", "reference-transaction"]
    assert report["required_gaps"] == []
    console_script = Path(str(report["python"])).with_name(
        "ethos.exe" if sys.platform == "win32" else "ethos"
    )
    version = subprocess.run(
        (console_script, "--version"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert version.returncode == 0, version.stderr
    assert version.stdout.strip()
    for name in report["scripts"]:
        text = (Path(str(report["hooks_path"])) / name).read_text(encoding="utf-8")
        assert text.startswith("#!/bin/sh\n")
        assert checkout_python.as_posix() not in text
        assert 'RUNTIME_ROOT="$HOOK_DIR/../../runtime"' in text
        assert 'CURRENT="$RUNTIME_ROOT/CURRENT"' in text
        assert 'exec "$RUNTIME/python/bin/python" -B -I -m ethos.cli' in text


def test_install_rejects_nonexistent_and_relative_python(tmp_path: Path) -> None:
    for python in (Path("python"), tmp_path / "missing-python"):
        with pytest.raises(ValueError, match="hook_runtime_python_invalid"):
            hook_activation.install_hook_launchers(tmp_path, python=python)


def test_install_rejects_unavailable_source_authority_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    python = tmp_path / "python"
    python.write_text("python", encoding="utf-8")
    materialized = False

    def unavailable(_root: Path):
        message = "hook_runtime_accepted_build_identity_unavailable"
        raise ValueError(message)

    def materialize(*_args: object, **_kwargs: object) -> Path:
        nonlocal materialized
        materialized = True
        return tmp_path / "runtime/python"

    monkeypatch.setattr(hook_activation, "expected_runtime_build", unavailable)
    monkeypatch.setattr(hook_activation.runtime_materialization, "materialize_runtime", materialize)

    with pytest.raises(ValueError, match="hook_runtime_accepted_build_identity_unavailable"):
        hook_activation.install_hook_launchers(tmp_path, python=python)

    assert materialized is False
