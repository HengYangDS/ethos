"""Owned Python runtime-image materialization contracts."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.materialization.python_environment as python_environment
import ethos.adapters.repo.runtime.materialization.python_image as python_image

if TYPE_CHECKING:
    from pathlib import Path


def _completed(code: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess((), code, stdout, stderr)


def test_owned_python_copy_rejects_interpreter_outside_its_base_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    interpreter = tmp_path / "foreign/python"
    interpreter.parent.mkdir()
    interpreter.write_bytes(b"python")
    monkeypatch.setattr(
        python_image,
        "observe_python_facts",
        lambda _python: {
            "python_abi": "cpython-test",
            "python_version": "3.14.7",
            "python_implementation": "cpython",
            "prefix": (tmp_path / "prefix").as_posix(),
            "base_prefix": (tmp_path / "base").as_posix(),
        },
    )

    with pytest.raises(ValueError, match="hook_runtime_owned_interpreter_unavailable"):
        python_image.materialize_python_image(
            tmp_path / "target",
            tmp_path,
            interpreter,
            tmp_path / "wheel",
            tmp_path / "work",
            locked=False,
        )


def test_python_observation_and_materialization_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    python = tmp_path / "python"
    python.write_bytes(b"python")
    monkeypatch.setattr(
        python_environment.subprocess,
        "run",
        lambda *_args, **_kwargs: _completed(1),
    )
    with pytest.raises(ValueError, match="hook_runtime_python_abi_invalid"):
        python_environment.observe_python_facts(python)

    monkeypatch.setattr(
        python_image,
        "observe_python_facts",
        lambda _python: {
            "python_abi": "cpython-test",
            "python_version": "3.14.7",
            "python_implementation": "cpython",
            "prefix": tmp_path.as_posix(),
            "base_prefix": tmp_path.as_posix(),
        },
    )
    (tmp_path / "lib/python3.14").mkdir(parents=True)
    monkeypatch.setattr(python_image.shutil, "copy2", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        python_image.shutil,
        "copytree",
        lambda _source, target, **_kwargs: target.mkdir(parents=True),
    )
    with pytest.raises(ValueError, match="hook_runtime_python_missing"):
        python_image.materialize_python_image(
            tmp_path / "runtime/python",
            tmp_path,
            python,
            tmp_path / "ethos.whl",
            tmp_path / "work",
            locked=True,
        )
