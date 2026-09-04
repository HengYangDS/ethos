"""Owned Python runtime-image materialization contracts."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.materialization.python_image as python_image
from ethos.adapters.repo.runtime.materialization.python_environment import file_sha256

if TYPE_CHECKING:
    from pathlib import Path


def _facts(prefix: Path, base: Path | None = None) -> dict[str, str]:
    return {
        "python_abi": "cpython-test",
        "python_version": "3.14.7",
        "python_implementation": "cpython",
        "architecture": "test",
        "prefix": str(prefix),
        "base_prefix": str(base or prefix),
    }


def _file(path: Path, content: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _fails(error: str, function, *args: object, **kwargs: object) -> None:
    with pytest.raises(ValueError, match=error):
        function(*args, **kwargs)


def test_python_copy_boundaries_and_windows_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    copy_tree = vars(python_image)["_copy_runtime_tree"]
    copy_file = vars(python_image)["_copy_runtime_file"]
    root, outside = tmp_path / "tree", _file(tmp_path / "outside")
    root.mkdir()
    _fails("interpreter_source_unavailable", copy_tree, outside, tmp_path / "target")
    invalid_links = (("absolute", outside), ("escape", "../outside"), ("missing", "missing"))
    for name, target in invalid_links:
        link = root / name
        link.symlink_to(target)
        _fails("python_symlink_invalid", copy_tree, root, tmp_path / name)
        _fails("python_symlink_invalid", copy_file, link, tmp_path / name)
        link.unlink()
    monkeypatch.setattr(python_image.shutil, "copy2", lambda *_a: None)
    regular, relative = _file(root / "regular"), root / "relative"
    relative.symlink_to("regular")
    for source in (regular, relative):
        copy_file(source, tmp_path / f"copy-{source.name}")
    directory = root / "directory"
    directory.mkdir()
    _fails("python_symlink_invalid", copy_file, directory, tmp_path / "copy")
    home, observed = tmp_path / "home", []
    copies: list[tuple[Path, Path]] = []
    interpreter = _file(home / "python.exe", b"python")
    for name in ("Lib", "DLLs"):
        (home / name).mkdir()
    for name in ("python3.dll", "vcruntime.dll"):
        _file(home / name, b"dll")
    monkeypatch.setattr(python_image, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        python_image.shutil,
        "copy2",
        lambda source, target: copies.append((source, target)),
    )
    for name in ("_copy_runtime_tree", "_copy_runtime_file"):
        monkeypatch.setattr(python_image, name, lambda source, _t: observed.append(source.name))
    vars(python_image)["_copy_python_runtime"](home, interpreter, tmp_path / "windows", "3.14.7")
    assert copies == [(interpreter, tmp_path / "windows/python.exe")]
    assert observed == ["Lib", "DLLs", "python3.dll", "vcruntime.dll"]


def test_console_script_discovery_and_rewrite_matrix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    python = _file(tmp_path / "runtime/bin/python", b"python")

    def entries(*items: tuple[str, str]) -> None:
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *_a, **_k: subprocess.CompletedProcess(
                (),
                0,
                json.dumps([[name, "v"] for group, name in items if group == "console_scripts"]),
                "",
            ),
        )

    entries(("other", "ignored"), ("console_scripts", "ethos"))
    assert python_image.console_script_entries(python) == {"ethos": "v"}
    for names in (("",), ("a/b",), ("a\\b",), ("dup", "dup")):
        entries(*(("console_scripts", name) for name in names))
        _fails("console_script_invalid", python_image.console_script_entries, python)
    rewrite = vars(python_image)["_rewrite_console_scripts"]
    monkeypatch.setattr(python_image, "runtime_python", lambda _r: python)
    monkeypatch.setattr(python_image, "console_script_entries", lambda _p: {})
    _fails("entrypoint_missing", rewrite, tmp_path / "runtime")
    monkeypatch.setattr(python_image, "console_script_entries", lambda _p: {"ethos": "v"})
    monkeypatch.setattr(python_image, "os", SimpleNamespace(name="nt"))
    windows_ethos = _file(python.parent / "ethos.exe")
    rewrite(tmp_path / "runtime")
    assert not windows_ethos.exists()
    monkeypatch.setattr(python_image, "os", SimpleNamespace(name="posix"))
    for kind in ("directory", "symlink"):
        artifact = python.parent / kind
        artifact.mkdir() if kind == "directory" else artifact.symlink_to("python")
        _fails("console_script_invalid", rewrite, tmp_path / "runtime")
        artifact.unlink() if artifact.is_symlink() else artifact.rmdir()
    ethos, legacy = _file(python.parent / "ethos"), python.parent / "legacy"
    _file(legacy, b"#!/bin/sh\n")
    rewrite(tmp_path / "runtime")
    assert not legacy.exists()
    assert not ethos.exists()


def test_console_script_discovery_uses_the_target_interpreter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    python = _file(tmp_path / "runtime/python.exe", b"python")
    observed: dict[str, object] = {}

    def execute(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed["command"] = command
        observed.update(kwargs)
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps([["ethos", "ethos.cli:main"]]),
            "",
        )

    monkeypatch.setattr(subprocess, "run", execute)

    assert python_image.console_script_entries(python) == {"ethos": "ethos.cli:main"}
    assert observed["command"][0] == python.as_posix()
    assert observed["command"][1:4] == ("-B", "-I", "-c")
    assert observed["capture_output"] is True
    assert observed["check"] is False
    assert observed["text"] is True


def test_package_runtime_source_identity_matrix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    check = vars(python_image)["_require_package_runtime_source"]
    source, runtime = tmp_path / "source", tmp_path / "runtime"
    wheel, interpreter = _file(tmp_path / "wheel"), _file(runtime / "python/bin/python", b"python")
    source.mkdir()
    lock = _file(source / "uv.lock", b"lock")
    valid = {
        "python": interpreter,
        "wheel_sha256": file_sha256(wheel),
        "dependency_lock_sha256": file_sha256(lock),
    }
    selected = SimpleNamespace(**valid)
    monkeypatch.setattr(python_image, "require_selected_runtime", lambda _r: selected)
    check(source, interpreter, wheel, _facts(runtime / "python"))
    for field, value, error in (
        ("python", tmp_path / "other", "interpreter_stale"),
        ("wheel_sha256", "0" * 64, "wheel_stale"),
        ("dependency_lock_sha256", "0" * 64, "lock_stale"),
    ):
        monkeypatch.setattr(selected, field, value)
        _fails(error, check, source, interpreter, wheel, _facts(runtime / "python"))
        monkeypatch.setattr(selected, field, valid[field])
