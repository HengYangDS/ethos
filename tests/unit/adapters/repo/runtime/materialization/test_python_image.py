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
    regular, relative = _file(root / "regular"), root / "relative"
    relative.symlink_to("regular")
    for source in (regular, relative):
        copied = tmp_path / f"copy-{source.name}"
        copy_file(source, copied)
        assert copied.read_bytes() == regular.read_bytes()
        assert not copied.is_symlink()
    directory = root / "directory"
    directory.mkdir()
    _fails("python_symlink_invalid", copy_file, directory, tmp_path / "copy")
    home, target = tmp_path / "home", tmp_path / "windows"
    interpreter = _file(home / "python.exe", b"python")
    for relative in ("Lib/os.py", "DLLs/_ssl.pyd", "python3.dll", "vcruntime.dll"):
        _file(home / relative, relative.encode())
    monkeypatch.setattr(python_image, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(python_image, "runtime_scripts", lambda root: root / "Scripts")
    vars(python_image)["_copy_python_runtime"](home, interpreter, target, "3.14.7")
    assert (target / "python.exe").read_bytes() == b"python"
    assert (target / "Scripts").is_dir()
    for relative in ("Lib/os.py", "DLLs/_ssl.pyd", "python3.dll", "vcruntime.dll"):
        assert (target / relative).read_bytes() == relative.encode()


@pytest.mark.parametrize(
    ("payload", "status", "gap"),
    [
        ('[["ethos","ethos.cli:main"]]', 0, ""),
        ("bad-json", 0, "entrypoint_missing"),
        ("{}", 0, "entrypoint_missing"),
        ("[]", 2, "entrypoint_missing"),
        *[
            (json.dumps(rows), 0, "console_script_invalid")
            for rows in (
                [None],
                [["ethos"]],
                [["ethos", 1]],
                [["", "v"]],
                [["a/b", "v"]],
                [["a\\b", "v"]],
                [["dup", "v"], ["dup", "v"]],
                [["ethos", ""]],
            )
        ],
    ],
)
def test_console_script_discovery_binds_target_and_rejects_invalid_entries(
    monkeypatch, tmp_path, payload, status, gap
):
    python = _file(tmp_path / "runtime/python.exe", b"python")

    def execute(command, **kwargs):
        assert command[:4] == (str(python), "-B", "-I", "-c")
        assert kwargs == {"capture_output": True, "check": False, "text": True}
        return subprocess.CompletedProcess(
            command, status, payload, "probe failed" if status else ""
        )

    monkeypatch.setattr(python_image.subprocess, "run", execute)
    if gap:
        _fails(gap, python_image.console_script_entries, python)
    else:
        assert python_image.console_script_entries(python) == {"ethos": "ethos.cli:main"}


def test_console_script_rewrite_preserves_binary_and_rejects_unowned_outputs(monkeypatch, tmp_path):
    python = _file(tmp_path / "runtime/bin/python", b"python")
    rewrite = vars(python_image)["_rewrite_console_scripts"]
    monkeypatch.setattr(python_image, "runtime_python", lambda _r: python)
    entries = {}
    monkeypatch.setattr(python_image, "console_script_entries", lambda _p: entries)
    _fails("entrypoint_missing", rewrite, tmp_path / "runtime")
    entries["ethos"] = "ethos.cli:main"
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
    entries["auxiliary"] = "package:main"
    binary = _file(python.parent / "auxiliary", b"native binary")
    _fails("console_script_invalid", rewrite, tmp_path / "runtime")
    assert binary.read_bytes() == b"native binary"
    binary.unlink()
    rewrite(tmp_path / "runtime")
    assert not legacy.exists()
    assert not ethos.exists()
    assert python.read_bytes() == b"python"
    assert binary.stat().st_mode & 0o111
    assert str(tmp_path) not in binary.read_text()
    assert '"$SCRIPT_DIR/python" -B -I' in binary.read_text()
    python.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n")
    python.chmod(0o755)
    executed = subprocess.run(
        [str(binary), "argument with spaces"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    arguments = executed.stdout.splitlines()
    assert arguments[:3] == ["-B", "-I", "-c"]
    assert arguments[-2:] == ["auxiliary", "argument with spaces"]


@pytest.mark.parametrize(
    "fault", ["none", "package", "interpreter", "wheel", "lock", "supply", "python", "virtual"]
)
def test_materialized_image_preserves_exact_source_and_requires_package_authority(
    tmp_path, monkeypatch, fault
):
    """Real image copy preserves source bytes and requires exact package or lock supply."""
    source, home, target = tmp_path / "source", tmp_path / "original/python", tmp_path / "image"
    interpreter = _file(home / "bin/python", b"python-runtime")
    for relative in (
        "lib/python3.14/os.py",
        "lib/python3.14/test/support.py",
        "include/Python.h",
        "share/python.1",
    ):
        _file(home / relative)
    _file(home / "lib/python3.14/site-packages/_yaml/__init__.py").chmod(0o444)
    library = _file(home / "lib/libpython3.14.1.dylib", b"library")
    (home / "lib/libpython3.14.dylib").symlink_to(library.name)
    (home / "lib/libpython3.14-directory").mkdir()
    wheel = _file(tmp_path / "wheel", b"wheel")
    lock = _file(source / "uv.lock", b"lock")
    entries = {"ethos": "ethos.cli:main", "uv": "uv:main"}
    selected = SimpleNamespace(
        python=interpreter,
        wheel_sha256=file_sha256(wheel),
        dependency_lock_sha256=file_sha256(lock),
    )
    monkeypatch.setattr(python_image, "require_selected_runtime", lambda _root: selected)
    monkeypatch.setattr(python_image, "console_script_entries", lambda _p: entries)
    before = {
        str(p.relative_to(home)): (p.read_bytes(), p.stat().st_mode)
        for p in home.rglob("*")
        if p.is_file()
    }
    facts = _facts(home)
    if fault in {"interpreter", "wheel", "lock"}:
        field = {
            "interpreter": "python",
            "wheel": "wheel_sha256",
            "lock": "dependency_lock_sha256",
        }[fault]
        setattr(selected, field, tmp_path / "other" if fault == "interpreter" else "0" * 64)
    elif fault == "virtual":
        facts["prefix"] = str(home / "venv")
    elif fault == "python":
        monkeypatch.setattr(python_image, "runtime_python", lambda _root: target / "missing")

    def install(_source, _dependency, python, _wheel, _requirements):
        assert (_source, _dependency, python, _wheel, _requirements) == (
            source,
            interpreter,
            target / "bin/python",
            wheel,
            lock,
        )
        for name in entries:
            _file(python.parent / name, f"#!{target}/staging-python\n".encode())
        _file(target / "lib/python3.14/site-packages/_yaml/__init__.py", b"installed")
        _file(target / "lib/python3.14/site-packages/ethos/__pycache__/module.pyc")
        _file(target / "lib/python3.14/obsolete.pyc")

    monkeypatch.setattr(python_image, "install_locked_runtime", install)

    def materialize(requirements):
        python_image.materialize_python_image(
            target,
            source,
            interpreter,
            wheel,
            dependency_python=None if fault == "supply" else interpreter,
            python_facts=facts,
            locked_requirements=requirements,
        )

    if fault in {"none", "package"}:
        materialize(lock if fault == "none" else None)
        assert (target / "lib/python3.14/site-packages/_yaml/__init__.py").read_bytes() == (
            b"installed" if fault == "none" else b"x"
        )
        assert not tuple(target.rglob("__pycache__")) + tuple(target.rglob("*.pyc"))
        assert not (target / "bin/ethos").exists()
        launcher = (target / "bin/uv").read_text()
        assert str(target) not in launcher
        assert '"$SCRIPT_DIR/python" -B -I' in launcher
    else:
        gap = {
            "supply": "dependency_supply_missing",
            "python": "python_missing",
            "virtual": "interpreter_source_unavailable",
        }.get(fault, f"package_{fault}_stale")
        _fails(gap, materialize, lock if fault == "supply" else None)
    assert {
        str(p.relative_to(home)): (p.read_bytes(), p.stat().st_mode)
        for p in home.rglob("*")
        if p.is_file()
    } == before
    if fault != "virtual":
        assert (target / "bin/python").read_bytes() == b"python-runtime"
        assert (target / "lib/libpython3.14.dylib").read_bytes() == b"library"
        assert not any(
            (target / path).exists() for path in ("include", "share", "lib/python3.14/test")
        )
    else:
        assert not target.exists()
